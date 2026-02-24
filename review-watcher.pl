#!/usr/bin/perl
# review-watcher.pl — Polls Smartsheet for new compliance review submissions,
# downloads PDFs, spawns Claude Code to process reviews, uploads results.
#
# Usage:
#   perl review-watcher.pl              # continuous polling mode
#   perl review-watcher.pl --once       # single poll cycle, then exit
#   perl review-watcher.pl --discover   # print sheet columns and IDs for config

use strict;
use warnings;
use HTTP::Tiny;
use JSON::PP;
use File::Path qw(make_path);
use File::Basename;
use Cwd 'abs_path';

my $ROOT = dirname(abs_path($0));
my $CONFIG_FILE = "$ROOT/review-config.json";
my $REVIEWS_DIR = "$ROOT/reviews";
my $API_BASE = 'https://api.smartsheet.com/2.0';

# --- Load config -----------------------------------------------------------

sub load_config {
    open my $fh, '<', $CONFIG_FILE
        or die "Cannot read $CONFIG_FILE: $!\nCopy review-config.json and fill in your Smartsheet API token and sheet ID.\n";
    local $/;
    my $json = <$fh>;
    close $fh;
    my $cfg = decode_json($json);
    die "smartsheet_token not set in $CONFIG_FILE\n"
        if !$cfg->{smartsheet_token} || $cfg->{smartsheet_token} eq 'YOUR_API_TOKEN_HERE';
    die "sheet_id not set in $CONFIG_FILE\n"
        if !$cfg->{sheet_id} || $cfg->{sheet_id} eq 'YOUR_SHEET_ID_HERE';
    return $cfg;
}

# --- HTTP helpers -----------------------------------------------------------

sub api_get {
    my ($http, $token, $path) = @_;
    my $url = $path =~ m{^https?://} ? $path : "$API_BASE$path";
    my $resp = $http->get($url, {
        headers => { 'Authorization' => "Bearer $token" }
    });
    if ($resp->{status} == 429) {
        print "  Rate limited, sleeping 60s...\n";
        sleep 60;
        return api_get($http, $token, $path);
    }
    return $resp;
}

sub api_put_json {
    my ($http, $token, $path, $data) = @_;
    my $body = encode_json($data);
    my $resp = $http->put("$API_BASE$path", {
        headers => {
            'Authorization' => "Bearer $token",
            'Content-Type'  => 'application/json',
        },
        content => $body,
    });
    if ($resp->{status} == 429) {
        print "  Rate limited, sleeping 60s...\n";
        sleep 60;
        return api_put_json($http, $token, $path, $data);
    }
    return $resp;
}

sub api_upload_file {
    my ($http, $token, $path, $filename, $data) = @_;
    my $resp = $http->post("$API_BASE$path", {
        headers => {
            'Authorization'       => "Bearer $token",
            'Content-Type'        => 'application/octet-stream',
            'Content-Disposition' => "attachment; filename=\"$filename\"",
            'Content-Length'      => length($data),
        },
        content => $data,
    });
    if ($resp->{status} == 429) {
        print "  Rate limited, sleeping 60s...\n";
        sleep 60;
        return api_upload_file($http, $token, $path, $filename, $data);
    }
    return $resp;
}

# --- Smartsheet helpers -----------------------------------------------------

sub get_cell_value {
    my ($row, $col_id) = @_;
    for my $cell (@{$row->{cells} || []}) {
        return $cell->{value} if defined $cell->{columnId} && $cell->{columnId} == $col_id;
    }
    return undef;
}

sub iso_now {
    my @t = gmtime;
    return sprintf('%04d-%02d-%02dT%02d:%02d:%02dZ',
        $t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0]);
}

sub make_job_id {
    my @t = localtime;
    return sprintf('%04d%02d%02d-%02d%02d%02d',
        $t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0]);
}

# --- Discover mode ----------------------------------------------------------

sub discover_mode {
    my $cfg = load_config();
    my $http = HTTP::Tiny->new(timeout => 30);
    my $resp = api_get($http, $cfg->{smartsheet_token}, "/sheets/$cfg->{sheet_id}");
    if (!$resp->{success}) {
        die "API error $resp->{status}: $resp->{content}\n";
    }
    my $sheet = decode_json($resp->{content});
    print "Sheet: $sheet->{name} (ID: $sheet->{id})\n\n";
    print "Columns:\n";
    printf "  %-30s  %-20s  %s\n", "Name", "Type", "Column ID";
    printf "  %-30s  %-20s  %s\n", "-" x 30, "-" x 20, "-" x 20;
    for my $col (@{$sheet->{columns} || []}) {
        printf "  %-30s  %-20s  %s\n", $col->{title}, $col->{type}, $col->{id};
    }
    print "\nCopy the Column IDs into review-config.json under \"columns\".\n";
    print "Match each column name to its config key:\n";
    print "  Project Name   -> projectName\n";
    print "  PM Email       -> pmEmail\n";
    print "  Review Phase   -> reviewPhase\n";
    print "  Construction Type -> constructionType\n";
    print "  Divisions      -> divisions\n";
    print "  Status         -> status\n";
    print "  Job ID         -> jobId\n";
    print "  Submitted      -> submitted\n";
    print "  Completed      -> completed\n";
    print "  Notes          -> notes\n";
}

# --- Update row cells -------------------------------------------------------

sub update_row {
    my ($http, $token, $sheet_id, $row_id, %updates) = @_;
    my @cells;
    for my $col_id (keys %updates) {
        push @cells, { columnId => int($col_id), value => $updates{$col_id} };
    }
    return api_put_json($http, $token, "/sheets/$sheet_id/rows", [
        { id => int($row_id), cells => \@cells }
    ]);
}

# --- Download PDF from row --------------------------------------------------

sub download_row_pdf {
    my ($http, $token, $sheet_id, $row_id, $dest_path) = @_;

    # List attachments on the row
    my $resp = api_get($http, $token, "/sheets/$sheet_id/rows/$row_id/attachments");
    if (!$resp->{success}) {
        return (undef, "Failed to list attachments: $resp->{status}");
    }
    my $att_list = decode_json($resp->{content});
    my @pdfs = grep { lc($_->{name}) =~ /\.pdf$/ } @{$att_list->{data} || []};
    if (!@pdfs) {
        return (undef, "No PDF attachment found on this row");
    }

    # Use the most recent PDF
    my $att = (sort { ($b->{createdAt} || '') cmp ($a->{createdAt} || '') } @pdfs)[0];

    # Get temporary download URL
    $resp = api_get($http, $token, "/sheets/$sheet_id/attachments/$att->{id}");
    if (!$resp->{success}) {
        return (undef, "Failed to get attachment URL: $resp->{status}");
    }
    my $att_detail = decode_json($resp->{content});
    my $url = $att_detail->{url};
    if (!$url) {
        return (undef, "No download URL in attachment response");
    }

    # Download the PDF (no auth header — it's a pre-signed URL)
    my $dl_http = HTTP::Tiny->new(timeout => 120);
    $resp = $dl_http->get($url);
    if (!$resp->{success}) {
        return (undef, "Failed to download PDF: $resp->{status}");
    }

    # Write to disk
    open my $fh, '>:raw', $dest_path or return (undef, "Cannot write $dest_path: $!");
    print $fh $resp->{content};
    close $fh;
    return ($att->{name}, undef);
}

# --- Upload report files to row ---------------------------------------------

sub upload_reports {
    my ($http, $token, $sheet_id, $row_id, $output_dir) = @_;
    my @uploaded;
    opendir my $dh, $output_dir or return @uploaded;
    while (my $f = readdir $dh) {
        next if $f =~ /^\./ || $f eq 'COMPLETE' || $f eq 'FAILED' || $f =~ /\.log$/;
        my $path = "$output_dir/$f";
        next unless -f $path;
        open my $fh, '<:raw', $path or next;
        local $/;
        my $data = <$fh>;
        close $fh;
        my $resp = api_upload_file($http, $token,
            "/sheets/$sheet_id/rows/$row_id/attachments", $f, $data);
        if ($resp->{success}) {
            push @uploaded, $f;
            print "    Uploaded: $f\n";
        } else {
            print "    Failed to upload $f: $resp->{status}\n";
        }
    }
    closedir $dh;
    return @uploaded;
}

# --- Spawn Claude review ----------------------------------------------------

sub list_standards_for_divs {
    my @divs = @_;
    my @files;
    for my $d (@divs) {
        my $dir = "$ROOT/standards/wsu/division-$d";
        if (opendir my $dh, $dir) {
            push @files, map { "standards/wsu/division-$d/$_" }
                         grep { /\.md$/ } readdir $dh;
            closedir $dh;
        }
    }
    return sort @files;
}

sub build_combined_standards {
    my ($job_dir, $group) = @_;
    my $outdir = "$job_dir/combined";
    make_path($outdir) unless -d $outdir;

    my @files = list_standards_for_divs(@{$group->{divs}});
    push @files, grep { -f "$ROOT/$_" } @{$group->{supp}};
    @files = sort @files;

    my $outfile = "$outdir/combined-$group->{key}.md";
    open my $fh, '>', $outfile or return '';
    print $fh "# Combined WSU Standards: $group->{name}\n";
    print $fh "# Total files: " . scalar(@files) . "\n\n";

    for my $f (@files) {
        my $path = "$ROOT/$f";
        if (open my $sfh, '<', $path) {
            print $fh "\n" . ("=" x 60) . "\n";
            print $fh "# SOURCE: $f\n";
            print $fh ("=" x 60) . "\n\n";
            local $/;
            my $content = <$sfh>;
            print $fh $content;
            close $sfh;
        }
    }
    close $fh;
    return $outfile;
}

sub spawn_review {
    my ($job_id, $job) = @_;
    my $job_dir    = "$REVIEWS_DIR/$job_id";
    my $output_dir = "$job_dir/output";
    make_path($output_dir) unless -d $output_dir;

    my $claude = $job->{claude_path};

    # --- Discipline group definitions ---
    my @ALL_GROUPS = (
        { key => 'architectural',    name => 'Architectural / Structure / Envelope / Finishes',
          divs => [qw(02 03 04 05 07 08 09 10 11 12 13 14)],
          desc => 'architectural, structural, envelope, roofing, doors/windows, finishes, specialties, and equipment sheets',
          supp => [] },
        { key => 'fire-protection',  name => 'Fire Protection and Security',
          divs => [qw(21 28)],
          desc => 'fire suppression, fire alarm, and electronic safety sheets',
          supp => [] },
        { key => 'plumbing',         name => 'Plumbing',
          divs => [qw(22)],
          desc => 'plumbing plans, fixture schedules, and domestic water sheets',
          supp => [] },
        { key => 'hvac-controls',    name => 'HVAC and Building Automation',
          divs => [qw(23 25)],
          desc => 'mechanical plans, HVAC equipment schedules, piping diagrams, and BAS/controls sequences',
          supp => [
              'standards/wsu/supplemental/detail-drawings/23-22-00-m1-steam-piping-diagrams.md',
              'standards/wsu/supplemental/detail-drawings/23-22-00-m2-steam-piping-schematic.md',
              'standards/wsu/supplemental/detail-drawings/23-83-13-heating-cable-schematic.md',
              'standards/wsu/supplemental/25-appendix-3-bas-point-naming.md',
              'standards/wsu/supplemental/25-appendix-4-standard-operating-procedures.md',
              'standards/wsu/supplemental/25-appendix-6-product-requirements.md',
              'standards/wsu/supplemental/25-appendix-7-airflow-control.md',
          ] },
        { key => 'electrical',       name => 'Electrical',
          divs => [qw(26)],
          desc => 'electrical plans, panel schedules, one-line diagrams, lighting plans, and power distribution sheets',
          supp => [
              'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting.md',
              'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting-pole-base.md',
          ] },
        { key => 'communications',   name => 'Communications and Technology',
          divs => [qw(27)],
          desc => 'telecommunications, data infrastructure, audio-visual, and technology system sheets',
          supp => [ 'standards/wsu/supplemental/27-technology-infrastructure-design-guide.md' ] },
        { key => 'civil-site',       name => 'Civil, Site, and Utilities',
          divs => [qw(31 32 33 40)],
          desc => 'civil, earthwork, exterior improvements, utilities, metering, and process integration sheets',
          supp => [
              'standards/wsu/supplemental/detail-drawings/32-33-13-bike-rack.md',
              'standards/wsu/supplemental/detail-drawings/33-01-33-energy-metering-diagram.md',
              'standards/wsu/supplemental/detail-drawings/33-05-13-standard-manhole.md',
              'standards/wsu/supplemental/detail-drawings/33-41-00-storm-drain-pipe.md',
              'standards/wsu/supplemental/detail-drawings/33-60-00-chilled-water-schematic.md',
              'standards/wsu/supplemental/detail-drawings/33-71-73-electric-meter-diagram.md',
          ] },
    );

    # Filter to groups containing user-selected divisions
    my %selected = map { $_ => 1 } @{$job->{divisions} || []};
    my @active;
    for my $g (@ALL_GROUPS) {
        my @match = grep { $selected{$_} } @{$g->{divs}};
        if (@match) {
            push @active, { %$g, active_divs => \@match };
        }
    }
    $job->{expectedGroups} = scalar @active;
    write_job_json($job_id, $job);

    # --- Build pre-concatenated standards per discipline ---
    for my $grp (@active) {
        build_combined_standards($job_dir, $grp);
    }

    # --- Write per-discipline prompt files (Phase 1) ---
    my $common_header = "Project: $job->{projectName}\n"
        . "Phase: $job->{reviewPhase}\n"
        . "Construction type: $job->{constructionType}\n\n";

    for my $grp (@active) {
        my $divs_str = join(', ', @{$grp->{active_divs}});
        my $combined_file = "reviews/$job_id/combined/combined-$grp->{key}.md";

        my $p = "You are reviewing construction drawings for WSU design standards compliance.\n";
        $p .= $common_header;
        $p .= "DISCIPLINE: $grp->{name} (Divisions $divs_str)\n";
        $p .= "Focus on: $grp->{desc}\n\n";
        $p .= "INSTRUCTIONS:\n";
        $p .= "1. Read the PDF at reviews/$job_id/input.pdf.\n";
        $p .= "   Focus on sheets relevant to this discipline but review the full drawing set for context.\n";
        $p .= "2. Read the combined standards file at $combined_file.\n";
        $p .= "   This file contains ALL WSU standards for this discipline — read it IN ITS ENTIRETY.\n";
        $p .= "3. For EVERY numbered requirement, clause, and sub-clause in the standards:\n";
        $p .= "   - Locate the relevant drawing sheet(s) in the PDF\n";
        $p .= "   - Assign status: [C] Compliant, [D] Deviation, [O] Omission, [X] Concern\n";
        $p .= "4. Write ALL findings to a SINGLE file: reviews/$job_id/output/discipline-$grp->{key}-findings.md\n";
        $p .= "   CRITICAL: Use exactly this filename. Do NOT split into multiple files. One file, all divisions.\n\n";
        $p .= "OUTPUT FORMAT:\n";
        $p .= "Begin with a summary table, then list every non-compliant finding as:\n";
        $p .= "  ### F-$grp->{key}-NNN: Title\n";
        $p .= "  - Division: XX\n";
        $p .= "  - CSI Code: XX XX XX\n";
        $p .= "  - Severity: Critical / Major / Minor\n";
        $p .= "  - Status: [D] / [O] / [X]\n";
        $p .= "  - PDF Reference: (page and sheet number)\n";
        $p .= "  - Standard Reference: (WSU standard section number)\n";
        $p .= "  - Issue: (detailed description)\n";
        $p .= "  - Required Action: (what must change)\n\n";
        $p .= "RULES:\n";
        $p .= "- Every finding MUST have both a PDF citation AND a WSU standard section citation.\n";
        $p .= "- Severity: Critical = life safety/code; Major = significant non-compliance; Minor = best-practice.\n";
        $p .= "- Be thorough — check EVERY requirement. Depth over speed.\n";

        my $pfile = "$job_dir/prompt-$grp->{key}.txt";
        open my $pf, '>', $pfile or next;
        print $pf $p;
        close $pf;
    }

    # --- Write synthesis prompt (Phase 2) ---
    {
        my $s = "You are synthesizing a WSU Design Standards compliance review.\n";
        $s .= $common_header;
        $s .= "The discipline-level reviews have been completed by parallel reviewers.\n";
        $s .= "Read ALL of these discipline findings files:\n";
        for my $grp (@active) {
            $s .= "  - reviews/$job_id/output/discipline-$grp->{key}-findings.md\n";
        }
        $s .= "\nRead the report templates:\n";
        $s .= "  - standards/REPORT-TEMPLATE-WORD.md\n";
        $s .= "  - standards/REPORT-TEMPLATE-EXCEL.md\n";
        $s .= "  - standards/CHECKLIST-TEMPLATE.md\n\n";
        $s .= "Generate these files in reviews/$job_id/output/:\n";
        $s .= "  (a) checklist.txt\n  (b) findings.txt (F-001, F-002, ... sorted by severity then division)\n";
        $s .= "  (c) notes.txt\n";
        $s .= "  (d) report.docx — Word document using python-docx (pip install if needed), following REPORT-TEMPLATE-WORD exactly\n";
        $s .= "  (e) report.xlsx — Excel workbook using openpyxl (pip install if needed), following REPORT-TEMPLATE-EXCEL exactly\n";
        $s .= "      Summary sheet MUST print on one 8.5x11 landscape page (fitToPage, fitToWidth=1, fitToHeight=1)\n";
        $s .= "  (f) COMPLETE sentinel\n\n";
        $s .= "FINDING INDEX (critical — enables cross-document traceability):\n";
        $s .= "- Every non-compliant finding gets one F-number (F-001, F-002, ...) assigned once, sorted by severity desc then division asc\n";
        $s .= "- findings.txt: F-### is the primary key, one entry per finding\n";
        $s .= "- report.docx Sections 5 & 6: same F-### in heading of each finding\n";
        $s .= "- report.xlsx Findings sheet: F-### in column A, one row per finding\n";
        $s .= "- report.xlsx Checklist sheet: 'Finding Ref' column links [D]/[O]/[X] rows to their F-###\n";
        $s .= "- report.xlsx Variances sheet: 'Finding Ref' column links V-## to F-###\n";
        $s .= "- report.docx Section 7: variance items reference their F-###\n";
        $s .= "- checklist.txt: non-compliant items include their F-### in the Notes column\n";
        $s .= "- Total finding count, severity breakdown, and F-numbers must be identical across ALL files\n\n";
        $s .= "RULES:\n";
        $s .= "- Preserve original PDF and standard citations exactly\n";
        $s .= "- Severity: Critical = life safety or code violation; Major = significant non-compliance; Minor = best-practice deviation\n";
        $s .= "- If any step fails, create FAILED with error description\n";

        open my $sf, '>', "$job_dir/prompt-synthesis.txt" or do { warn "Cannot write synthesis prompt: $!\n"; return; };
        print $sf $s;
        close $sf;
    }

    # --- Write multi-phase bash script ---
    my $script = "$job_dir/run-review.sh";
    open my $fh, '>', $script or do { warn "Cannot write $script: $!\n"; return; };

    print $fh "#!/bin/bash\n";
    print $fh "# Multi-phase parallel review: $job_id\n";
    print $fh "unset CLAUDECODE\n";
    print $fh "export CLAUDE_CODE_GIT_BASH_PATH='C:\\Users\\john.slagboom\\AppData\\Local\\Programs\\Git\\bin\\bash.exe'\n";
    print $fh "cd \"$ROOT\"\n\n";

    # Phase 1: parallel discipline CLIs
    print $fh "echo \"Phase 1: Launching " . scalar(@active) . " discipline scans...\" > \"$output_dir/progress.log\"\n\n";

    for my $grp (@active) {
        my $pfile  = "$job_dir/prompt-$grp->{key}.txt";
        my $stdout = "$output_dir/$grp->{key}-stdout.log";
        my $stderr = "$output_dir/$grp->{key}-stderr.log";

        (my $var_key = uc($grp->{key})) =~ s/-/_/g;  # bash-safe var name
        print $fh "PROMPT_${var_key}=\$(cat \"$pfile\")\n";
        print $fh "\"$claude\" -p \"\$PROMPT_${var_key}\" \\\n";
        print $fh "  --model sonnet \\\n";
        print $fh "  --dangerously-skip-permissions \\\n";
        print $fh "  --output-format text \\\n";
        print $fh "  > \"$stdout\" \\\n";
        print $fh "  2> \"$stderr\" &\n\n";
    }

    print $fh "wait\n";
    print $fh "echo \"Phase 1 complete.\" >> \"$output_dir/progress.log\"\n\n";

    # Check for failures
    print $fh "FOUND=0\n";
    print $fh "for f in \"$output_dir\"/discipline-*-findings.md; do\n";
    print $fh "  [ -f \"\$f\" ] && FOUND=\$((FOUND + 1))\n";
    print $fh "done\n";
    print $fh "if [ \"\$FOUND\" -eq 0 ]; then\n";
    print $fh "  echo \"No discipline findings produced.\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n\n";

    # Phase 2: synthesis
    print $fh "echo \"Phase 2: Synthesizing reports...\" >> \"$output_dir/progress.log\"\n";
    print $fh "SYNTH_PROMPT=\$(cat \"$job_dir/prompt-synthesis.txt\")\n";
    print $fh "\"$claude\" -p \"\$SYNTH_PROMPT\" \\\n";
    print $fh "  --dangerously-skip-permissions \\\n";
    print $fh "  --output-format text \\\n";
    print $fh "  > \"$output_dir/synthesis-stdout.log\" \\\n";
    print $fh "  2> \"$output_dir/synthesis-stderr.log\"\n\n";
    print $fh "echo \"Review complete.\" >> \"$output_dir/progress.log\"\n";

    close $fh;
    chmod 0755, $script;

    my $group_names = join(', ', map { $_->{name} } @active);
    print "  Spawning parallel review for job $job_id...\n";
    print "  Architecture: " . scalar(@active) . " parallel CLIs (Sonnet) + synthesis\n";
    print "  Groups: $group_names\n";
    system(qq{bash "$script" &});
}

# --- Job JSON helpers -------------------------------------------------------

sub write_job_json {
    my ($job_id, $job) = @_;
    my $path = "$REVIEWS_DIR/$job_id/job.json";
    open my $fh, '>', $path or die "Cannot write $path: $!\n";
    print $fh JSON::PP->new->pretty->encode($job);
    close $fh;
}

sub read_job_json {
    my ($job_id) = @_;
    my $path = "$REVIEWS_DIR/$job_id/job.json";
    return undef unless -f $path;
    open my $fh, '<', $path or return undef;
    local $/;
    my $json = <$fh>;
    close $fh;
    return decode_json($json);
}

# --- Poll cycle -------------------------------------------------------------

sub poll_cycle {
    my ($cfg) = @_;
    my $http = HTTP::Tiny->new(timeout => 30);
    my $token = $cfg->{smartsheet_token};
    my $sheet_id = $cfg->{sheet_id};
    my $cols = $cfg->{columns};

    print "[" . localtime() . "] Polling sheet $sheet_id...\n";

    # 1. Fetch sheet with attachments
    my $resp = api_get($http, $token, "/sheets/$sheet_id?include=attachments");
    if (!$resp->{success}) {
        print "  API error $resp->{status}: " . substr($resp->{content} || '', 0, 200) . "\n";
        return;
    }
    my $sheet = decode_json($resp->{content});
    my @rows = @{$sheet->{rows} || []};

    # 2. Find "Submitted" rows
    my @submitted;
    for my $row (@rows) {
        my $status = get_cell_value($row, $cols->{status}) || '';
        push @submitted, $row if $status eq 'Submitted';
    }

    # 3. Check processing jobs for completion
    make_path($REVIEWS_DIR) unless -d $REVIEWS_DIR;
    if (opendir my $dh, $REVIEWS_DIR) {
        while (my $dir = readdir $dh) {
            next if $dir =~ /^\./;
            my $job = read_job_json($dir);
            next unless $job && $job->{status} eq 'Processing';

            my $complete_file = "$REVIEWS_DIR/$dir/output/COMPLETE";
            my $failed_file = "$REVIEWS_DIR/$dir/output/FAILED";

            if (-f $complete_file) {
                print "  Job $dir: COMPLETE\n";
                # Upload reports to Smartsheet
                my @uploaded = upload_reports($http, $token, $sheet_id,
                    $job->{rowId}, "$REVIEWS_DIR/$dir/output");
                # Update Smartsheet row
                update_row($http, $token, $sheet_id, $job->{rowId},
                    $cols->{status}    => 'Complete',
                    $cols->{completed} => iso_now(),
                    $cols->{notes}     => "Reports: " . join(', ', @uploaded),
                );
                $job->{status} = 'Complete';
                $job->{completed} = iso_now();
                $job->{outputFiles} = \@uploaded;
                write_job_json($dir, $job);
            }
            elsif (-f $failed_file) {
                print "  Job $dir: FAILED\n";
                my $err = '';
                if (open my $fh, '<', "$REVIEWS_DIR/$dir/output/claude-stderr.log") {
                    local $/; $err = <$fh>; close $fh;
                }
                $err = substr($err, 0, 500) if length($err) > 500;
                $err ||= 'Unknown error — check claude-stderr.log';
                update_row($http, $token, $sheet_id, $job->{rowId},
                    $cols->{status} => 'Failed',
                    $cols->{completed} => iso_now(),
                    $cols->{notes}  => "Error: $err",
                );
                $job->{status} = 'Failed';
                $job->{completed} = iso_now();
                $job->{error} = $err;
                write_job_json($dir, $job);
            }
            else {
                print "  Job $dir: still processing...\n";
            }
        }
        closedir $dh;
    }

    # 4. Process new submissions (one at a time)
    if (@submitted) {
        my $row = $submitted[0];  # oldest first (Smartsheet returns top-to-bottom)
        my $project = get_cell_value($row, $cols->{projectName}) || 'Unnamed Project';
        my $email = get_cell_value($row, $cols->{pmEmail}) || '';
        my $phase = get_cell_value($row, $cols->{reviewPhase}) || '';
        my $type = get_cell_value($row, $cols->{constructionType}) || '';
        my $divs_str = get_cell_value($row, $cols->{divisions}) || '';
        my @divs = map { s/^\s+|\s+$//gr } split(/,/, $divs_str);

        my $job_id = make_job_id();
        print "  New submission: \"$project\" -> job $job_id\n";

        # Create job directory
        my $job_dir = "$REVIEWS_DIR/$job_id";
        make_path("$job_dir/output");

        # Download PDF
        my ($pdf_name, $pdf_err) = download_row_pdf(
            $http, $token, $sheet_id, $row->{id}, "$job_dir/input.pdf");

        if ($pdf_err) {
            print "  ERROR: $pdf_err\n";
            update_row($http, $token, $sheet_id, $row->{id},
                $cols->{status} => 'Failed',
                $cols->{jobId}  => $job_id,
                $cols->{notes}  => $pdf_err,
            );
            write_job_json($job_id, {
                id => $job_id, rowId => $row->{id}, projectName => $project,
                status => 'Failed', error => $pdf_err, submitted => iso_now(),
            });
            return;
        }

        print "  Downloaded: $pdf_name\n";

        # Update Smartsheet: Processing
        update_row($http, $token, $sheet_id, $row->{id},
            $cols->{status} => 'Processing',
            $cols->{jobId}  => $job_id,
        );

        # Write job metadata
        my $job = {
            id               => $job_id,
            rowId            => $row->{id},
            projectName      => $project,
            pmEmail          => $email,
            reviewPhase      => $phase,
            constructionType => $type,
            divisions        => \@divs,
            status           => 'Processing',
            submitted        => iso_now(),
            completed        => undef,
            pdfFilename      => $pdf_name,
            claude_path      => $cfg->{claude_path},
        };
        write_job_json($job_id, $job);

        # Spawn Claude
        spawn_review($job_id, $job);
    }
    else {
        print "  No pending submissions.\n";
    }
}

# --- Main -------------------------------------------------------------------

if (grep { $_ eq '--discover' } @ARGV) {
    discover_mode();
    exit 0;
}

my $once = grep { $_ eq '--once' } @ARGV;

my $cfg = load_config();
make_path($REVIEWS_DIR) unless -d $REVIEWS_DIR;

print "WSU Compliance Review Watcher\n";
print "  Sheet ID: $cfg->{sheet_id}\n";
print "  Claude:   $cfg->{claude_path}\n";
print "  Reviews:  $REVIEWS_DIR\n";
print "  Mode:     " . ($once ? 'single poll' : "continuous (every $cfg->{poll_interval_seconds}s)") . "\n\n";

if ($once) {
    poll_cycle($cfg);
    print "\nDone.\n";
}
else {
    while (1) {
        eval { poll_cycle($cfg) };
        if ($@) {
            print "  Poll error: $@\n";
        }
        print "  Sleeping $cfg->{poll_interval_seconds}s...\n\n";
        sleep($cfg->{poll_interval_seconds});
    }
}
