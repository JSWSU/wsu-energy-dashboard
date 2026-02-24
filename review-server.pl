#!/usr/bin/perl
# review-server.pl — HTTP server for WSU Compliance Review Portal.
# Serves the review-portal.html frontend and handles API routes for
# PDF upload, job tracking, and report downloads.
#
# Usage: perl review-server.pl [port]   (default 8083)

use strict;
use warnings;
use IO::Socket::INET;
use JSON::PP;
use File::Path qw(make_path);
use File::Basename;
use Cwd 'abs_path';

my $port = $ARGV[0] || 8083;
my $ROOT = dirname(abs_path($0));
my $REVIEWS_DIR = "$ROOT/reviews";
my $CLAUDE_PATH = '';

# Auto-detect Claude CLI
{
    my $appdata = $ENV{APPDATA} || '';
    $appdata =~ s{\\}{/}g;  # normalize to forward slashes for MSYS Perl
    for my $candidate (
        "$appdata/Claude/claude-code/claude.exe",
        glob("$appdata/Claude/claude-code/*/claude.exe"),
    ) {
        if (-f $candidate) { $CLAUDE_PATH = $candidate; last; }
    }
    if (!$CLAUDE_PATH) {
        my $which = `which claude 2>/dev/null`;
        chomp $which;
        $CLAUDE_PATH = $which if $which && -f $which;
    }
    die "Cannot find Claude CLI. Set \$CLAUDE_PATH in review-server.pl.\n" unless $CLAUDE_PATH;
}

make_path($REVIEWS_DIR) unless -d $REVIEWS_DIR;

my %mime = (
    html => 'text/html',       css  => 'text/css',
    js   => 'application/javascript', json => 'application/json',
    png  => 'image/png',       jpg  => 'image/jpeg',
    gif  => 'image/gif',       svg  => 'image/svg+xml',
    ico  => 'image/x-icon',    txt  => 'text/plain',
    md   => 'text/markdown',   pdf  => 'application/pdf',
    docx => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    pptx => 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    xlsx => 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
);

my $srv = IO::Socket::INET->new(
    LocalAddr => '0.0.0.0', LocalPort => $port,
    Proto => 'tcp', Listen => 5, ReuseAddr => 1,
) or die "Cannot bind to port $port: $!\n";

print "WSU Review Portal Server\n";
print "  Root:   $ROOT\n";
print "  Claude: $CLAUDE_PATH\n";
print "  URL:    http://localhost:$port/review-portal.html\n\n";

# --- Helpers ----------------------------------------------------------------

sub iso_now {
    my @t = localtime;
    return sprintf('%04d-%02d-%02dT%02d:%02d:%02d',
        $t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0]);
}

sub make_job_id {
    my @t = localtime;
    return sprintf('%04d%02d%02d-%02d%02d%02d',
        $t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0]);
}

sub send_response {
    my ($c, $code, $ct, $body) = @_;
    my $status = $code == 200 ? 'OK' : $code == 201 ? 'Created' : $code == 204 ? 'No Content'
        : $code == 400 ? 'Bad Request' : $code == 404 ? 'Not Found'
        : $code == 413 ? 'Payload Too Large' : $code == 500 ? 'Internal Server Error' : 'Error';
    print $c "HTTP/1.0 $code $status\r\n"
        . "Content-Type: $ct\r\n"
        . "Content-Length: " . length($body) . "\r\n"
        . "Access-Control-Allow-Origin: *\r\n"
        . "\r\n"
        . $body;
}

sub send_json {
    my ($c, $code, $data) = @_;
    send_response($c, $code, 'application/json', encode_json($data));
}

sub read_exact {
    my ($sock, $len) = @_;
    my $buf = '';
    while (length($buf) < $len) {
        my $n = read($sock, my $chunk, $len - length($buf));
        last unless $n;
        $buf .= $chunk;
    }
    return $buf;
}

# --- Multipart parser -------------------------------------------------------

sub parse_multipart {
    my ($body, $boundary) = @_;
    my $delim = "--$boundary";
    my (%fields, %files);

    my @parts = split(/\Q$delim\E/, $body);
    shift @parts;   # empty before first boundary
    pop @parts;     # closing "--\r\n"

    for my $part (@parts) {
        $part =~ s/^\r\n//;
        my ($hdr_block, $content) = split(/\r\n\r\n/, $part, 2);
        next unless defined $content;
        $content =~ s/\r\n$//;

        my ($name) = $hdr_block =~ /name="([^"]+)"/;
        my ($filename) = $hdr_block =~ /filename="([^"]+)"/;
        next unless $name;

        if ($filename) {
            $files{$name} = { filename => $filename, data => $content };
        } else {
            $fields{$name} = $content;
        }
    }
    return (\%fields, \%files);
}

# --- Job helpers ------------------------------------------------------------

sub write_job_json {
    my ($job_id, $job) = @_;
    my $path = "$REVIEWS_DIR/$job_id/job.json";
    open my $fh, '>', $path or return;
    print $fh JSON::PP->new->pretty->canonical->encode($job);
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
    return eval { decode_json($json) };
}

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
    print $fh "# This file contains ALL standard files for this discipline group.\n";
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

sub check_job_status {
    my ($job_id) = @_;
    my $job = read_job_json($job_id);
    return undef unless $job;
    return $job unless ($job->{status} || '') eq 'Processing';

    my $complete = "$REVIEWS_DIR/$job_id/output/COMPLETE";
    my $failed   = "$REVIEWS_DIR/$job_id/output/FAILED";
    my $job_dir  = "$REVIEWS_DIR/$job_id";

    if (-f $complete) {
        $job->{status} = 'Complete';
        $job->{progress} = 100;
        $job->{completed} = iso_now();
        my @out;
        if (opendir my $dh, "$job_dir/output") {
            @out = grep { !/^\./ && $_ ne 'COMPLETE' && $_ ne 'FAILED' && $_ !~ /\.log$/ }
                   readdir $dh;
            closedir $dh;
        }
        $job->{outputFiles} = [sort @out];
        write_job_json($job_id, $job);
    }
    elsif (-f $failed) {
        $job->{status} = 'Failed';
        $job->{progress} = 0;
        $job->{completed} = iso_now();
        my $err = '';
        if (open my $fh, '<', "$job_dir/output/claude-stderr.log") {
            local $/; $err = <$fh>; close $fh;
        }
        $job->{error} = substr($err, 0, 2000) || 'Unknown error';
        write_job_json($job_id, $job);
    }
    else {
        # Progress milestones:
        #   5%  = Job submitted
        #  15%  = Discipline scans running
        #  30%  = Checklist generated
        #  50%  = Findings generated
        #  65%  = Notes generated
        #  85%  = Excel report generated
        #  95%  = All outputs done
        # 100%  = COMPLETE

        my $pct = 5;
        my $expected = $job->{expectedGroups} || 0;

        # Phase 1: discipline scans (5% to 15%)
        my $done = 0;
        if ($expected > 0 && opendir my $dh, "$job_dir/output") {
            $done = scalar grep { /^discipline-.*-findings\.md$/ } readdir $dh;
            closedir $dh;
            if ($done > 0) {
                $pct = 15;
            }
        }

        # Phase 2: synthesis milestones (30% to 95%)
        my $in_synthesis = -f "$job_dir/output/synthesis-stdout.log";
        if ($in_synthesis || ($done == $expected && $expected > 0)) {
            $pct = 15 unless $pct > 15;
            $pct = 30  if -f "$job_dir/output/checklist.txt";
            $pct = 50  if -f "$job_dir/output/findings.txt";
            $pct = 65  if -f "$job_dir/output/notes.txt";
            $pct = 75  if -f "$job_dir/output/report.docx";
            $pct = 85  if -f "$job_dir/output/report.xlsx";
            $pct = 95  if -f "$job_dir/output/report.xlsx"
                        && -f "$job_dir/output/report.docx"
                        && -f "$job_dir/output/notes.txt"
                        && -f "$job_dir/output/findings.txt"
                        && -f "$job_dir/output/checklist.txt";
        }

        $job->{progress} = $pct;

        # Stall detection: find newest file mtime in output/
        my $newest_mtime = 0;
        if (opendir my $dh2, "$job_dir/output") {
            for my $f (readdir $dh2) {
                next if $f =~ /^\./;
                my $mt = (stat "$job_dir/output/$f")[9] || 0;
                $newest_mtime = $mt if $mt > $newest_mtime;
            }
            closedir $dh2;
        }
        if ($newest_mtime > 0) {
            my $idle = int((time() - $newest_mtime) / 60);
            $job->{stalledMinutes} = $idle if $idle >= 10;
        }
    }
    return $job;
}

# --- Spawn Claude -----------------------------------------------------------

sub spawn_review {
    my ($job_id, $job) = @_;
    my $job_dir    = "$REVIEWS_DIR/$job_id";
    my $output_dir = "$job_dir/output";
    make_path($output_dir) unless -d $output_dir;

    # --- Discipline group definitions ---
    my @ALL_GROUPS = (
        {
            key  => 'architectural',
            name => 'Architectural / Structure / Envelope / Finishes',
            divs => [qw(02 03 04 05 07 08 09 10 11 12 13 14)],
            desc => 'architectural, structural, envelope, roofing, doors/windows, finishes, specialties, and equipment sheets',
            supp => [],
        },
        {
            key  => 'fire-protection',
            name => 'Fire Protection and Security',
            divs => [qw(21 28)],
            desc => 'fire suppression, fire alarm, and electronic safety sheets',
            supp => [],
        },
        {
            key  => 'plumbing',
            name => 'Plumbing',
            divs => [qw(22)],
            desc => 'plumbing plans, fixture schedules, and domestic water sheets',
            supp => [],
        },
        {
            key  => 'hvac-controls',
            name => 'HVAC and Building Automation',
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
            ],
        },
        {
            key  => 'electrical',
            name => 'Electrical',
            divs => [qw(26)],
            desc => 'electrical plans, panel schedules, one-line diagrams, lighting plans, and power distribution sheets',
            supp => [
                'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting.md',
                'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting-pole-base.md',
            ],
        },
        {
            key  => 'communications',
            name => 'Communications and Technology',
            divs => [qw(27)],
            desc => 'telecommunications, data infrastructure, audio-visual, and technology system sheets',
            supp => [
                'standards/wsu/supplemental/27-technology-infrastructure-design-guide.md',
            ],
        },
        {
            key  => 'civil-site',
            name => 'Civil, Site, and Utilities',
            divs => [qw(31 32 33 40)],
            desc => 'civil, earthwork, exterior improvements, utilities, metering, and process integration sheets',
            supp => [
                'standards/wsu/supplemental/detail-drawings/32-33-13-bike-rack.md',
                'standards/wsu/supplemental/detail-drawings/33-01-33-energy-metering-diagram.md',
                'standards/wsu/supplemental/detail-drawings/33-05-13-standard-manhole.md',
                'standards/wsu/supplemental/detail-drawings/33-41-00-storm-drain-pipe.md',
                'standards/wsu/supplemental/detail-drawings/33-60-00-chilled-water-schematic.md',
                'standards/wsu/supplemental/detail-drawings/33-71-73-electric-meter-diagram.md',
            ],
        },
    );

    # Filter to groups containing user-selected divisions
    my %selected = map { $_ => 1 } @{$job->{divisions} || []};
    my @active;
    for my $g (@ALL_GROUPS) {
        my @match = grep { $selected{$_} } @{$g->{divs}};
        if (@match) {
            push @active, {
                %$g,
                active_divs => \@match,
            };
        }
    }

    # Store expected group count for progress tracking
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
        $p .= "Begin with a summary table:\n";
        $p .= "  | Metric | Count |\n";
        $p .= "  | Total requirements evaluated | N |\n";
        $p .= "  | Compliant [C] | N |\n";
        $p .= "  | Deviations [D] | N |\n";
        $p .= "  | Omissions [O] | N |\n";
        $p .= "  | Concerns [X] | N |\n\n";

        $p .= "Then list every non-compliant finding as:\n";
        $p .= "  ### F-$grp->{key}-NNN: Title\n";
        $p .= "  - Division: XX\n";
        $p .= "  - CSI Code: XX XX XX\n";
        $p .= "  - Severity: Critical / Major / Minor\n";
        $p .= "  - Status: [D] / [O] / [X]\n";
        $p .= "  - PDF Reference: (page and sheet number)\n";
        $p .= "  - Standard Reference: (WSU standard section number)\n";
        $p .= "  - Issue: (detailed description of the non-compliance)\n";
        $p .= "  - Required Action: (what the designer must change)\n\n";

        $p .= "RULES:\n";
        $p .= "- Every finding MUST have both a PDF page/sheet citation AND a WSU standard section citation.\n";
        $p .= "- Severity: Critical = life safety or code violation; Major = significant WSU standard non-compliance; Minor = best-practice deviation.\n";
        $p .= "- If the discipline has no sheets in the drawings, note which requirements cannot be verified.\n";
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
        $s .= "\n";

        $s .= "Read the report templates:\n";
        $s .= "  - standards/REPORT-TEMPLATE-WORD.md\n";
        $s .= "  - standards/REPORT-TEMPLATE-EXCEL.md\n";
        $s .= "  - standards/CHECKLIST-TEMPLATE.md\n\n";

        $s .= "Generate these files in reviews/$job_id/output/:\n";
        $s .= "  (a) checklist.txt — filled checklist template, one row per requirement across all disciplines\n";
        $s .= "  (b) findings.txt — all findings with sequential F-numbers (F-001, F-002, ...) sorted by severity then division\n";
        $s .= "  (c) notes.txt — methodology notes, drawing inventory, applicability determinations\n";
        $s .= "  (d) report.docx — Word document using python-docx (pip install if needed), following REPORT-TEMPLATE-WORD exactly\n";
        $s .= "  (e) report.xlsx — Excel workbook using openpyxl (pip install if needed), following REPORT-TEMPLATE-EXCEL exactly\n";
        $s .= "      The Summary sheet MUST be configured to print on one 8.5x11 landscape page:\n";
        $s .= "        ws.page_setup.orientation = 'landscape'\n";
        $s .= "        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER\n";
        $s .= "        ws.page_setup.fitToPage = True\n";
        $s .= "        ws.page_setup.fitToWidth = 1\n";
        $s .= "        ws.page_setup.fitToHeight = 1\n";
        $s .= "        ws.sheet_properties.pageSetUpPr.fitToPage = True\n";
        $s .= "  (f) COMPLETE — create this empty sentinel file ONLY after all other outputs are written\n\n";

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
        $s .= "- Every checklist row in checklist.txt must also appear in the Excel Checklist sheet\n";
        $s .= "- Preserve original PDF and standard citations exactly as the discipline reviewers wrote them\n";
        $s .= "- Severity: Critical = life safety or code violation; Major = significant WSU standard non-compliance; Minor = best-practice deviation\n";
        $s .= "- If any step fails, create reviews/$job_id/output/FAILED with a description of the error\n";

        my $sfile = "$job_dir/prompt-synthesis.txt";
        open my $sf, '>', $sfile or do { warn "Cannot write synthesis prompt: $!\n"; return; };
        print $sf $s;
        close $sf;
    }

    # --- Also write combined prompt.txt for debugging ---
    {
        open my $dbg, '>', "$job_dir/prompt.txt" or warn "Cannot write prompt.txt: $!\n";
        if ($dbg) {
            print $dbg "=== PARALLEL CLI ARCHITECTURE ===\n";
            print $dbg "Phase 1: " . scalar(@active) . " parallel Claude CLIs (Sonnet) for discipline scans\n";
            print $dbg "Phase 2: 1 Claude CLI (default model) for synthesis\n\n";
            for my $grp (@active) {
                print $dbg "--- prompt-$grp->{key}.txt ---\n";
                if (open my $rf, '<', "$job_dir/prompt-$grp->{key}.txt") {
                    local $/; my $c = <$rf>; print $dbg $c; close $rf;
                }
                print $dbg "\n\n";
            }
            print $dbg "--- prompt-synthesis.txt ---\n";
            if (open my $rf, '<', "$job_dir/prompt-synthesis.txt") {
                local $/; my $c = <$rf>; print $dbg $c; close $rf;
            }
            close $dbg;
        }
    }

    # --- Write multi-phase bash script ---
    my $script = "$job_dir/run-review.sh";
    open my $fh, '>', $script or do {
        warn "Cannot write $script: $!\n";
        return;
    };

    # Script header
    print $fh "#!/bin/bash\n";
    print $fh "# Multi-phase parallel review: $job_id\n";
    print $fh "# Phase 1: " . scalar(@active) . " parallel discipline scans (Sonnet)\n";
    print $fh "# Phase 2: Synthesis and report generation\n\n";
    print $fh "unset CLAUDECODE\n";
    print $fh "export CLAUDE_CODE_GIT_BASH_PATH='C:\\Users\\john.slagboom\\AppData\\Local\\Programs\\Git\\bin\\bash.exe'\n";
    print $fh "cd \"$ROOT\"\n\n";

    # Phase 1: parallel discipline CLIs
    print $fh "# === PHASE 1: Parallel discipline scans ===\n";
    print $fh "echo \"Phase 1: Launching " . scalar(@active) . " discipline scans...\" > \"$output_dir/progress.log\"\n\n";

    for my $grp (@active) {
        my $pfile   = "$job_dir/prompt-$grp->{key}.txt";
        my $stdout  = "$output_dir/$grp->{key}-stdout.log";
        my $stderr  = "$output_dir/$grp->{key}-stderr.log";

        (my $var_key = uc($grp->{key})) =~ s/-/_/g;  # bash-safe var name
        print $fh "# Discipline: $grp->{name}\n";
        print $fh "echo \"Launching: $grp->{name}...\"\n";
        print $fh "PROMPT_${var_key}=\$(cat \"$pfile\")\n";
        print $fh "\"$CLAUDE_PATH\" -p \"\$PROMPT_${var_key}\" \\\n";
        print $fh "  --model sonnet \\\n";
        print $fh "  --dangerously-skip-permissions \\\n";
        print $fh "  --output-format text \\\n";
        print $fh "  > \"$stdout\" \\\n";
        print $fh "  2> \"$stderr\" &\n\n";
    }

    print $fh "# Wait for all discipline scans to complete\n";
    print $fh "echo \"Waiting for all " . scalar(@active) . " discipline scans...\"\n";
    print $fh "wait\n";
    print $fh "echo \"Phase 1 complete: all discipline scans finished.\" >> \"$output_dir/progress.log\"\n\n";

    # Check for failures
    print $fh "# Check if any discipline produced findings\n";
    print $fh "FOUND=0\n";
    print $fh "for f in \"$output_dir\"/discipline-*-findings.md; do\n";
    print $fh "  [ -f \"\$f\" ] && FOUND=\$((FOUND + 1))\n";
    print $fh "done\n";
    print $fh "if [ \"\$FOUND\" -eq 0 ]; then\n";
    print $fh "  echo \"ERROR: No discipline findings files were produced. Check stderr logs.\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n";
    print $fh "echo \"Phase 1 produced \$FOUND discipline findings files.\"\n\n";

    # Phase 2: synthesis
    print $fh "# === PHASE 2: Synthesis and report generation ===\n";
    print $fh "echo \"Phase 2: Synthesizing reports...\" >> \"$output_dir/progress.log\"\n";
    my $synth_prompt = "$job_dir/prompt-synthesis.txt";
    my $synth_stdout = "$output_dir/synthesis-stdout.log";
    my $synth_stderr = "$output_dir/synthesis-stderr.log";
    print $fh "SYNTH_PROMPT=\$(cat \"$synth_prompt\")\n";
    print $fh "\"$CLAUDE_PATH\" -p \"\$SYNTH_PROMPT\" \\\n";
    print $fh "  --dangerously-skip-permissions \\\n";
    print $fh "  --output-format text \\\n";
    print $fh "  > \"$synth_stdout\" \\\n";
    print $fh "  2> \"$synth_stderr\"\n\n";

    print $fh "echo \"Review complete.\" >> \"$output_dir/progress.log\"\n";

    close $fh;
    chmod 0755, $script;

    my $group_names = join(', ', map { $_->{name} } @active);
    print "[" . localtime() . "] Spawning parallel review for job $job_id\n";
    print "  Architecture: " . scalar(@active) . " parallel CLIs (Sonnet) + synthesis\n";
    print "  Groups: $group_names\n";
    print "  Script: $script\n";
    system(qq{bash "$script" &});
}

# --- Request handler --------------------------------------------------------

while (my $c = $srv->accept) {
    binmode $c;

    # Read request line
    my $req_line = <$c>;
    next unless $req_line && $req_line =~ m{^(GET|POST|OPTIONS)\s+(/\S*)\s+HTTP};
    my ($method, $path) = ($1, $2);
    $path =~ s/\?.*//;  # strip query string

    # Read all headers
    my %headers;
    while (my $hdr = <$c>) {
        $hdr =~ s/\r?\n$//;
        last if $hdr eq '';
        if ($hdr =~ /^([^:]+):\s*(.*)/) {
            $headers{lc $1} = $2;
        }
    }

    # CORS preflight
    if ($method eq 'OPTIONS') {
        print $c "HTTP/1.0 204 No Content\r\n"
            . "Access-Control-Allow-Origin: *\r\n"
            . "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            . "Access-Control-Allow-Headers: Content-Type\r\n"
            . "\r\n";
        close $c;
        next;
    }

    # Read body for POST
    my $body = '';
    if ($method eq 'POST' && $headers{'content-length'}) {
        my $len = int($headers{'content-length'});
        if ($len > 104_857_600) {  # 100MB
            send_json($c, 413, { error => 'File too large (100MB max)' });
            close $c;
            next;
        }
        $body = read_exact($c, $len);
    }

    # --- API Routes ---------------------------------------------------------

    # POST /api/submit — new review submission
    if ($method eq 'POST' && $path eq '/api/submit') {
        my $ct = $headers{'content-type'} || '';
        my ($boundary) = $ct =~ /boundary=(.+)/;
        if (!$boundary) {
            send_json($c, 400, { error => 'Expected multipart/form-data' });
            close $c;
            next;
        }

        my ($fields, $files) = parse_multipart($body, $boundary);
        my $project = $fields->{projectName} || '';
        my $divs_str = $fields->{divisions} || '';
        my $phase = $fields->{reviewPhase} || '';
        my $type = $fields->{constructionType} || '';
        my $email = $fields->{pmEmail} || '';
        my $pdf = $files->{pdf};

        if (!$project) {
            send_json($c, 400, { error => 'Project name is required' });
            close $c; next;
        }
        if (!$divs_str) {
            send_json($c, 400, { error => 'At least one division must be selected' });
            close $c; next;
        }
        if (!$pdf || !$pdf->{data}) {
            send_json($c, 400, { error => 'PDF file is required' });
            close $c; next;
        }
        if (lc($pdf->{filename}) !~ /\.pdf$/) {
            send_json($c, 400, { error => 'File must be a PDF' });
            close $c; next;
        }

        my $job_id = make_job_id();
        my $job_dir = "$REVIEWS_DIR/$job_id";
        make_path("$job_dir/output");

        # Save PDF
        open my $fh, '>:raw', "$job_dir/input.pdf" or do {
            send_json($c, 500, { error => "Cannot save PDF: $!" });
            close $c; next;
        };
        print $fh $pdf->{data};
        close $fh;

        my @divs = map { s/^\s+|\s+$//gr } split(/,/, $divs_str);
        my $job = {
            id               => $job_id,
            projectName      => $project,
            pmEmail          => $email,
            reviewPhase      => $phase,
            constructionType => $type,
            divisions        => \@divs,
            status           => 'Processing',
            submitted        => iso_now(),
            completed        => undef,
            pdfFilename      => $pdf->{filename},
        };
        write_job_json($job_id, $job);
        spawn_review($job_id, $job);

        send_json($c, 201, { id => $job_id, status => 'Processing' });
        close $c;
        next;
    }

    # GET /api/jobs — list all jobs
    if ($method eq 'GET' && $path eq '/api/jobs') {
        my @jobs;
        if (opendir my $dh, $REVIEWS_DIR) {
            while (my $dir = readdir $dh) {
                next if $dir =~ /^\./;
                my $j = check_job_status($dir);
                push @jobs, $j if $j;
            }
            closedir $dh;
        }
        @jobs = sort { ($b->{submitted} || '') cmp ($a->{submitted} || '') } @jobs;
        send_json($c, 200, \@jobs);
        close $c;
        next;
    }

    # GET /api/jobs/{id}
    if ($method eq 'GET' && $path =~ m{^/api/jobs/([a-zA-Z0-9_-]+)$}) {
        my $id = $1;
        my $j = check_job_status($id);
        if ($j) {
            send_json($c, 200, $j);
        } else {
            send_json($c, 404, { error => 'Job not found' });
        }
        close $c;
        next;
    }

    # GET /api/download/{id}/{filename}
    if ($method eq 'GET' && $path =~ m{^/api/download/([a-zA-Z0-9_-]+)/([a-zA-Z0-9._-]+)$}) {
        my ($id, $filename) = ($1, $2);
        $filename =~ s/[^a-zA-Z0-9._-]//g;  # sanitize
        my $file = "$REVIEWS_DIR/$id/output/$filename";
        if (-f $file) {
            open my $fh, '<:raw', $file or do {
                send_json($c, 500, { error => 'Cannot read file' });
                close $c; next;
            };
            local $/; my $data = <$fh>; close $fh;
            my ($ext) = $filename =~ /\.(\w+)$/;
            my $ct = $mime{lc($ext || '')} || 'application/octet-stream';
            send_response($c, 200, $ct, $data);
        } else {
            send_json($c, 404, { error => 'File not found' });
        }
        close $c;
        next;
    }

    # --- Static file serving ------------------------------------------------
    if ($method eq 'GET') {
        $path = '/review-portal.html' if $path eq '/';
        $path =~ s{/\.\.}{}g;
        my $file = "$ROOT$path";

        if (-f $file) {
            open my $fh, '<:raw', $file or do {
                send_response($c, 500, 'text/plain', 'Cannot read file');
                close $c; next;
            };
            local $/; my $data = <$fh>; close $fh;
            my ($ext) = $file =~ /\.(\w+)$/;
            my $ct = $mime{lc($ext || '')} || 'application/octet-stream';
            send_response($c, 200, $ct, $data);
        } else {
            send_response($c, 404, 'text/plain', "404 Not Found: $path");
        }
    }
    else {
        send_response($c, 405, 'text/plain', 'Method not allowed');
    }

    close $c;
}
