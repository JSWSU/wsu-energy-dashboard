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

sub spawn_review {
    my ($job_id, $job) = @_;
    my $output_dir = "$REVIEWS_DIR/$job_id/output";
    make_path($output_dir) unless -d $output_dir;

    my $claude = $job->{claude_path};
    my $divs = join(', ', @{$job->{divisions} || []});

    my $prompt = "Process compliance review job $job_id. "
        . "Read the PDF at reviews/$job_id/input.pdf. "
        . "Project: $job->{projectName}. "
        . "Divisions: $divs. "
        . "Phase: $job->{reviewPhase}. "
        . "Construction type: $job->{constructionType}. "
        . "Follow the wsu-compliance-review workflow. "
        . "Read standards/INDEX.md first. "
        . "Write all outputs (checklist.md, findings.md, report-word.md, report-ppt.md, notes.md) "
        . "to reviews/$job_id/output/. "
        . "Create reviews/$job_id/output/COMPLETE when all outputs are written. "
        . "If you encounter an error, create reviews/$job_id/output/FAILED with the error description.";

    # Escape single quotes for shell
    $prompt =~ s/'/'\\''/g;

    # Build command — use cd to set working directory, spawn in background
    my $stdout_log = "$output_dir/claude-stdout.log";
    my $stderr_log = "$output_dir/claude-stderr.log";

    my $cmd = qq{unset CLAUDECODE && export CLAUDE_CODE_GIT_BASH_PATH='C:\\Users\\john.slagboom\\AppData\\Local\\Programs\\Git\\bin\\bash.exe' && cd "$ROOT" && "$claude" -p '$prompt' }
        . qq{--dangerously-skip-permissions }
        . qq{--output-format text }
        . qq{> "$stdout_log" }
        . qq{2> "$stderr_log" }
        . qq{&};

    print "  Spawning Claude for job $job_id...\n";
    system($cmd);
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
