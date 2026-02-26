#!/usr/bin/perl
# review-server.pl — HTTP server for WSU Compliance Review Portal.
# Serves the review-portal.html frontend and handles API routes for
# PDF upload, job tracking, and report downloads.
#
# Usage: perl review-server.pl [port]   (default 8083)

use strict;
use warnings;
use IO::Socket::INET;
use IO::Select;
use JSON::PP;
use File::Path qw(make_path remove_tree);
use File::Basename;
use Cwd 'abs_path';
use Net::SMTP;

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
    my ($sock, $len, $timeout) = @_;
    $timeout ||= 120;  # default 120s for body reads
    my $sel = IO::Select->new($sock);
    my $buf = '';
    while (length($buf) < $len) {
        unless ($sel->can_read($timeout)) {
            warn "[TIMEOUT] read_exact timed out after ${timeout}s with " . length($buf) . "/$len bytes\n";
            last;
        }
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
    my $tmp  = "$path.tmp";
    open my $fh, '>', $tmp or return;
    print $fh JSON::PP->new->pretty->canonical->encode($job);
    close $fh;
    unlink $path if -f $path;  # Windows rename() cannot overwrite
    rename $tmp, $path;
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

# --- Email notification -----------------------------------------------------

my $_email_cfg;   # cached config

sub load_email_config {
    return $_email_cfg if $_email_cfg;
    my $path = "$ROOT/email-config.json";
    return undef unless -f $path;
    open my $fh, '<', $path or do { warn "[EMAIL] Cannot read $path: $!\n"; return undef; };
    local $/;
    my $json = <$fh>;
    close $fh;
    $_email_cfg = eval { decode_json($json) };
    if ($@) { warn "[EMAIL] Invalid JSON in $path: $@\n"; $_email_cfg = undef; }
    return $_email_cfg;
}

sub send_completion_email {
    my ($job_id, $job) = @_;

    # Guard: already sent
    return if $job->{emailSent};

    # Guard: no email address provided
    my $to = $job->{pmEmail} || '';
    $to =~ s/^\s+|\s+$//g;
    return unless $to =~ /.+\@.+/;

    # Guard: config disabled or missing
    my $cfg = load_email_config();
    return unless $cfg && $cfg->{enabled};

    my $project  = $job->{projectName} || 'Unnamed Project';
    my $phase    = $job->{reviewPhase} || '';
    my $portal   = $cfg->{portal_url} || 'http://localhost:8083/review-portal.html';
    my @files    = @{$job->{outputFiles} || []};
    my $file_list = join("\n", map { "  - $_" } @files) || '  (none)';

    my $subject  = "Review Complete: $project" . ($phase ? " ($phase)" : '');
    my $from_name = $cfg->{from_name} || 'WSU Review Portal';
    my $from_addr = $cfg->{from_address} || $cfg->{smtp_user};
    my $reply_to  = $cfg->{reply_to} || $from_addr;

    my $body = "Hello,\n\n"
        . "The compliance review for your project is complete.\n\n"
        . "  Project:  $project\n"
        . "  Phase:    $phase\n"
        . "  Job ID:   $job_id\n\n"
        . "Deliverables ready for download:\n$file_list\n\n"
        . "Download your reports from the Review Portal:\n"
        . "  $portal\n\n"
        . "Navigate to the Review Queue tab and look for Job ID $job_id.\n\n"
        . "---\n"
        . "WSU Facilities Services\n"
        . "Design Standards Compliance Review Portal\n";

    eval {
        my $smtp = Net::SMTP->new(
            $cfg->{smtp_host},
            Port    => $cfg->{smtp_port} || 587,
            Timeout => 30,
            Debug   => 0,
        ) or die "Cannot connect to $cfg->{smtp_host}:$cfg->{smtp_port}: $@\n";

        if ($cfg->{smtp_starttls}) {
            $smtp->starttls() or die "STARTTLS failed: " . $smtp->message() . "\n";
        }

        if ($cfg->{smtp_user}) {
            $smtp->auth($cfg->{smtp_user}, $cfg->{smtp_pass})
                or die "SMTP auth failed: " . $smtp->message() . "\n";
        }

        $smtp->mail($from_addr) or die "MAIL FROM failed: " . $smtp->message() . "\n";
        $smtp->to($to)          or die "RCPT TO failed: " . $smtp->message() . "\n";

        $smtp->data()            or die "DATA failed: " . $smtp->message() . "\n";
        $smtp->datasend("From: $from_name <$from_addr>\r\n");
        $smtp->datasend("To: $to\r\n");
        $smtp->datasend("Reply-To: $reply_to\r\n");
        $smtp->datasend("Subject: $subject\r\n");
        $smtp->datasend("MIME-Version: 1.0\r\n");
        $smtp->datasend("Content-Type: text/plain; charset=UTF-8\r\n");
        $smtp->datasend("\r\n");
        $smtp->datasend($body);
        $smtp->dataend()         or die "DATA END failed: " . $smtp->message() . "\n";

        $smtp->quit();
    };

    if ($@) {
        my $err = "$@";
        chomp $err;
        warn "[EMAIL] Failed for job $job_id ($to): $err\n";
        $job->{emailError} = $err;
        write_job_json($job_id, $job);
        return;
    }

    $job->{emailSent} = JSON::PP::true;
    $job->{emailSentAt} = iso_now();
    delete $job->{emailError};
    write_job_json($job_id, $job);
    print "[EMAIL] Sent completion notification for job $job_id to $to\n";
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
        # Only list final deliverables (not intermediate discipline files, scripts, etc.)
        # Supports both old (.md) and new (.txt) naming for backward compatibility
        my @deliverables = qw(
            checklist.txt findings.txt notes.txt
            checklist.md  findings.md  notes.md
            report.docx report.xlsx
        );
        my @out = grep { -f "$job_dir/output/$_" } @deliverables;
        $job->{outputFiles} = \@out;
        write_job_json($job_id, $job);
        send_completion_email($job_id, $job);
    }
    elsif (-f $failed) {
        $job->{status} = 'Failed';
        $job->{progress} = 0;
        $job->{completed} = iso_now();

        # Read primary error from FAILED file
        my $err = '';
        if (open my $fh, '<', $failed) {
            local $/; $err = <$fh>; close $fh;
        }
        $job->{error} = $err || 'Unknown error';

        # Scan for non-empty stderr log files
        my @error_logs;
        if (opendir my $dh, "$job_dir/output") {
            for my $f (sort readdir $dh) {
                next unless $f =~ /-stderr\.log$/;
                my $path = "$job_dir/output/$f";
                if (-f $path && -s $path) {
                    push @error_logs, $f;
                }
            }
            closedir $dh;
        }
        $job->{errorLogs} = \@error_logs if @error_logs;

        # Determine failed phase by checking which outputs exist
        my $has_findings = 0;
        if (opendir my $dh, "$job_dir/output") {
            $has_findings = scalar grep { /^discipline-.*-findings\.json$/ } readdir $dh;
            closedir $dh;
        }
        my $has_review_data = -f "$job_dir/output/review-data.json";
        my $has_reports = -f "$job_dir/output/report.docx";

        if (!$has_findings) {
            $job->{failedPhase} = 'Phase 1 (discipline scanning)';
            $job->{completedPhases} = [];
        } elsif (!$has_review_data) {
            $job->{failedPhase} = 'Phase 2 (synthesis)';
            $job->{completedPhases} = ['Phase 1: Discipline scanning'];
        } elsif (!$has_reports) {
            $job->{failedPhase} = 'Phase 3 (report generation)';
            $job->{completedPhases} = ['Phase 1: Discipline scanning', 'Phase 2: Synthesis'];
        } else {
            $job->{failedPhase} = 'Finalization';
            $job->{completedPhases} = ['Phase 1: Discipline scanning', 'Phase 2: Synthesis', 'Phase 3: Report generation'];
        }

        write_job_json($job_id, $job);
    }
    else {
        # 3-phase progress milestones:
        # Phase 1: discipline scans (5% -> 12%)
        #   5%  = Job submitted
        #   7%  = stdout logs exist (CLIs launched, scanning)
        #  7-12 = partial discipline findings arriving
        #  12%  = All discipline JSON files exist
        # Phase 2: synthesis (15% -> 50%)
        #  15%  = synthesis-stdout.log exists (synthesis started)
        #  50%  = review-data.json exists
        # Phase 3: local generation (60% -> 95%)
        #  60%  = report.docx exists
        #  70%  = report.xlsx exists
        #  80%  = checklist.txt exists
        #  85%  = findings.txt exists
        #  90%  = notes.txt exists
        #  95%  = all 5 deliverables exist
        # 100%  = COMPLETE

        my $pct = 5;
        my $detail = '';
        my $expected = $job->{expectedGroups} || 0;

        # Phase 1: discipline scans (5% to 12%)
        my $done = 0;
        my $scanning = 0;
        if ($expected > 0 && opendir my $dh, "$job_dir/output") {
            my @files = readdir $dh;
            closedir $dh;
            $done = scalar grep { /^discipline-.*-findings\.json$/ } @files;
            # Count stdout logs (excluding synthesis) as early "scanning started" signal
            $scanning = scalar grep { /-stdout\.log$/ && !/^synthesis-/ } @files;

            if ($done >= $expected) {
                $pct = 12;
                $detail = "All $expected disciplines scanned";
            } elsif ($done > 0) {
                $pct = 7 + int(5 * $done / $expected);
                $detail = "Scanning: $done of $expected disciplines complete";
            } elsif ($scanning > 0) {
                $pct = 7;
                $detail = "Scanning $expected disciplines...";
            }
        }

        # Phase 2: synthesis (15% to 50%)
        my $in_synthesis = -f "$job_dir/output/synthesis-stdout.log";
        if ($in_synthesis || ($done >= $expected && $expected > 0)) {
            $pct = 15 unless $pct > 15;
            $detail = "Synthesizing findings...";
            if (-f "$job_dir/output/review-data.json") {
                $pct = 50;
                $detail = "Review data merged";
            }
        }

        # Phase 3: local report generation (60% to 95%)
        if (-f "$job_dir/output/review-data.json") {
            $pct = 50 unless $pct > 50;
            $detail = "Generating reports..." unless $pct > 50;
            if (-f "$job_dir/output/report.docx") {
                $pct = 60; $detail = "Generating reports...";
            }
            if (-f "$job_dir/output/report.xlsx") {
                $pct = 70; $detail = "Generating reports...";
            }
            if (-f "$job_dir/output/checklist.txt") {
                $pct = 80; $detail = "Generating reports...";
            }
            if (-f "$job_dir/output/findings.txt") {
                $pct = 85; $detail = "Validating...";
            }
            if (-f "$job_dir/output/notes.txt") {
                $pct = 90; $detail = "Finalizing...";
            }
            if (-f "$job_dir/output/report.xlsx"
                && -f "$job_dir/output/report.docx"
                && -f "$job_dir/output/notes.txt"
                && -f "$job_dir/output/findings.txt"
                && -f "$job_dir/output/checklist.txt") {
                $pct = 95; $detail = "Finalizing...";
            }
        }

        $job->{progress} = $pct;
        $job->{progressDetail} = $detail if $detail;

        # Per-discipline status
        if ($job->{disciplineGroups} && ref($job->{disciplineGroups}) eq 'ARRAY') {
            my @disc_status;
            for my $grp (@{$job->{disciplineGroups}}) {
                my $key = $grp->{key};
                my $findings_file = "$job_dir/output/discipline-$key-findings.json";
                my $stdout_file   = "$job_dir/output/$key-stdout.log";
                my $status = 'pending';
                my $completed_at;
                if (-f $findings_file) {
                    $status = 'complete';
                    $completed_at = (stat $findings_file)[9];
                } elsif (-f $stdout_file) {
                    $status = 'scanning';
                }
                my $entry = { key => $key, name => $grp->{name}, status => $status };
                $entry->{completedAt} = $completed_at if $completed_at;
                push @disc_status, $entry;
            }
            $job->{disciplineStatus} = \@disc_status;
        }

        # Elapsed time
        $job->{elapsedSeconds} = time() - $job->{submittedEpoch} if $job->{submittedEpoch};

        # Phase-aware stall detection + auto-fail
        # Phase 1 (pct < 15): stall 45min, auto-fail 60min
        # Phase 2 (pct 15-49): stall 30min, auto-fail 45min
        # Phase 3 (pct >= 50): stall 15min, auto-fail 30min
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
            my ($stall_thresh, $fail_thresh, $phase_name);
            if ($pct < 15) {
                $stall_thresh = 45; $fail_thresh = 60;
                $phase_name = 'Phase 1 (discipline scanning)';
            } elsif ($pct < 50) {
                $stall_thresh = 30; $fail_thresh = 45;
                $phase_name = 'Phase 2 (synthesis)';
            } else {
                $stall_thresh = 15; $fail_thresh = 30;
                $phase_name = 'Phase 3 (report generation)';
            }

            if ($idle >= $fail_thresh) {
                # Auto-fail: write descriptive FAILED file
                my $fail_msg = "AUTO-FAIL: Stalled in $phase_name for $idle minutes "
                    . "(threshold: ${fail_thresh}min). Last file activity: "
                    . scalar(localtime($newest_mtime));
                open my $ff, '>', "$job_dir/output/FAILED" or warn "Cannot write FAILED: $!\n";
                if ($ff) { print $ff $fail_msg; close $ff; }
                $job->{status} = 'Failed';
                $job->{error} = $fail_msg;
                $job->{failedPhase} = $phase_name;
                $job->{completed} = iso_now();
                write_job_json($job_id, $job);
            } elsif ($idle >= $stall_thresh) {
                $job->{stalledMinutes} = $idle;
                $job->{stalledPhase} = $phase_name;
            }
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
            key  => 'arch-structure',
            name => 'Architectural — Structure & Envelope',
            divs => [qw(02 03 04 05 07 08)],
            desc => 'demolition, concrete, masonry, metals, roofing, waterproofing, and openings sheets',
            supp => [],
        },
        {
            key  => 'arch-finishes',
            name => 'Architectural — Finishes & Equipment',
            divs => [qw(09 10 11 12 13 14)],
            desc => 'finishes, specialties, equipment, furnishings, special construction, and conveying sheets',
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

    # Store expected group count and discipline metadata for progress tracking
    $job->{expectedGroups} = scalar @active;
    $job->{disciplineGroups} = [ map { { key => $_->{key}, name => $_->{name} } } @active ];
    $job->{submittedEpoch} = time();
    write_job_json($job_id, $job);

    # --- Build pre-concatenated standards per discipline ---
    for my $grp (@active) {
        build_combined_standards($job_dir, $grp);
    }

    # --- Write per-discipline prompt files (Phase 1) ---
    my $job_rel = "reviews/$job_id";
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
        $p .= "1. Read the extracted page text files in $job_rel/pages/.\n";
        $p .= "   Start by reading $job_rel/pages/manifest.txt for the page list.\n";
        $p .= "   Focus on pages relevant to this discipline but review all pages for context.\n";
        $p .= "   These are pre-extracted text from the construction drawings PDF.\n";
        $p .= "2. Read the combined standards file at $combined_file.\n";
        $p .= "   This file contains ALL WSU standards for this discipline — read it IN ITS ENTIRETY.\n";
        $p .= "3. For EVERY numbered requirement, clause, and sub-clause in the standards:\n";
        $p .= "   - Locate the relevant drawing sheet(s) in the PDF\n";
        $p .= "   - Assign status: [C] Compliant, [D] Deviation, [O] Omission, [X] Concern\n";
        $p .= "4. Write a SINGLE JSON file to: reviews/$job_id/output/discipline-$grp->{key}-findings.json\n";
        $p .= "   CRITICAL: Use exactly this filename. Do NOT split into multiple files. One file, all divisions.\n\n";

        my $divs_json = join(', ', map { "\"$_\"" } @{$grp->{active_divs}});

        $p .= "OUTPUT FORMAT:\n";
        $p .= "Write a single valid JSON file matching this exact schema:\n";
        $p .= "{\n";
        $p .= "  \"discipline\": \"$grp->{key}\",\n";
        $p .= "  \"divisions_reviewed\": [$divs_json],\n";
        $p .= "  \"summary\": {\n";
        $p .= "    \"total_requirements\": N,\n";
        $p .= "    \"compliant\": N,\n";
        $p .= "    \"deviations\": N,\n";
        $p .= "    \"omissions\": N,\n";
        $p .= "    \"concerns\": N\n";
        $p .= "  },\n";
        $p .= "  \"requirements\": [\n";
        $p .= "    {\n";
        $p .= "      \"division\": \"XX\",\n";
        $p .= "      \"csi_code\": \"XX XX XX\",\n";
        $p .= "      \"requirement\": \"Description of standard requirement\",\n";
        $p .= "      \"status\": \"C|D|O|X\",\n";
        $p .= "      \"severity\": \"Critical|Major|Minor|null\",\n";
        $p .= "      \"finding_id\": \"F-$grp->{key}-NNN or null\",\n";
        $p .= "      \"pdf_reference\": \"Page N (Sheet-ID)\",\n";
        $p .= "      \"standard_reference\": \"WSU section citation\",\n";
        $p .= "      \"issue\": \"Description or null\",\n";
        $p .= "      \"required_action\": \"Action or null\",\n";
        $p .= "      \"drawing_sheet\": \"Sheet reference or null\",\n";
        $p .= "      \"notes\": \"\"\n";
        $p .= "    }\n";
        $p .= "  ]\n";
        $p .= "}\n\n";
        $p .= "CRITICAL: Output MUST be valid JSON. Include ALL requirements (both compliant and non-compliant).\n";
        $p .= "For compliant requirements: status=\"C\", severity=null, finding_id=null, issue=null, required_action=null.\n";
        $p .= "Summary counts MUST match: total_requirements = compliant + deviations + omissions + concerns.\n\n";

        $p .= "RULES:\n";
        $p .= "- Every non-compliant finding MUST have both a PDF page/sheet citation AND a WSU standard section citation.\n";
        $p .= "- Severity: Critical = life safety or code violation; Major = significant WSU standard non-compliance; Minor = best-practice deviation.\n";
        $p .= "- If the discipline has no sheets in the drawings, note which requirements cannot be verified.\n";
        $p .= "- Be thorough — check EVERY requirement. Depth over speed.\n";

        my $pfile = "$job_dir/prompt-$grp->{key}.txt";
        open my $pf, '>', $pfile or next;
        print $pf $p;
        close $pf;
    }

    # --- Write executive summary prompt (Phase 2b) ---
    # Phase 2a is now Python (synthesize.py). Phase 2b uses Haiku for the exec summary.
    {
        my $s = "Read the file synthesis-stats.txt in the current directory.\n";
        $s .= "Write a 2-3 paragraph executive summary for this WSU Design Standards compliance review.\n";
        $s .= "Be professional and succinct. Address the project manager directly.\n";
        $s .= "Cover: overall scope, key findings by severity, compliance percentage, and recommended next steps.\n";
        $s .= "Do NOT repeat every finding — direct the reader to the full report for details.\n";
        $s .= "Output ONLY the executive summary text, no JSON, no headings, no markdown.\n";

        my $sfile = "$job_dir/prompt-exec-summary.txt";
        open my $sf, '>', $sfile or do { warn "Cannot write exec summary prompt: $!\n"; return; };
        print $sf $s;
        close $sf;
    }

    # --- Also write combined prompt.txt for debugging ---
    {
        open my $dbg, '>', "$job_dir/prompt.txt" or warn "Cannot write prompt.txt: $!\n";
        if ($dbg) {
            print $dbg "=== PIPELINE ARCHITECTURE ===\n";
            print $dbg "Phase 0: PDF text extraction (one-time, pdfplumber)\n";
            print $dbg "Phase 1: " . scalar(@active) . " parallel Claude CLIs (Sonnet) -> JSON findings\n";
            print $dbg "Phase 2a: Python synthesize.py -> review-data.json (zero tokens)\n";
            print $dbg "Phase 2b: Claude CLI (Haiku) -> executive-summary.txt\n";
            print $dbg "Phase 3: Local Python (generate_reports.py) -> .docx + .xlsx + .txt\n\n";
            for my $grp (@active) {
                print $dbg "--- prompt-$grp->{key}.txt ---\n";
                if (open my $rf, '<', "$job_dir/prompt-$grp->{key}.txt") {
                    local $/; my $c = <$rf>; print $dbg $c; close $rf;
                }
                print $dbg "\n\n";
            }
            print $dbg "--- prompt-exec-summary.txt (Phase 2b) ---\n";
            if (open my $rf, '<', "$job_dir/prompt-exec-summary.txt") {
                local $/; my $c = <$rf>; print $dbg $c; close $rf;
            }
            print $dbg "\n\n--- Phase 3 ---\n";
            print $dbg "Local report generation: python generate_reports.py review-data.json\n";
            close $dbg;
        }
    }

    # --- Write review bash script ---
    my $script = "$job_dir/run-review.sh";
    my $expected_count = scalar @active;
    open my $fh, '>', $script or do {
        warn "Cannot write $script: $!\n";
        return;
    };

    # Script header
    print $fh "#!/bin/bash\n";
    print $fh "# Multi-phase parallel review: $job_id\n";
    print $fh "# Phase 0:  PDF text extraction (one-time, pdfplumber)\n";
    print $fh "# Phase 1:  $expected_count parallel discipline scans (Sonnet) -> JSON\n";
    print $fh "# Phase 2a: Python synthesis -> review-data.json (zero tokens)\n";
    print $fh "# Phase 2b: Claude Haiku -> executive-summary.txt\n";
    print $fh "# Phase 3:  Local Python -> .docx + .xlsx + .txt (zero tokens)\n\n";
    print $fh "unset CLAUDECODE\n";

    # Dynamic Git Bash discovery for CLAUDE_CODE_GIT_BASH_PATH
    print $fh "GIT_BASH=\"\"\n";
    print $fh "for candidate in \\\n";
    print $fh "  \"\$PROGRAMFILES/Git/bin/bash.exe\" \\\n";
    print $fh "  \"/c/Program Files/Git/bin/bash.exe\" \\\n";
    print $fh "  \"\$LOCALAPPDATA/Programs/Git/bin/bash.exe\" \\\n";
    print $fh "  \"/c/Users/\$USERNAME/AppData/Local/Programs/Git/bin/bash.exe\"; do\n";
    print $fh "  [ -f \"\$candidate\" ] && { GIT_BASH=\"\$candidate\"; break; }\n";
    print $fh "done\n";
    print $fh "if [ -n \"\$GIT_BASH\" ]; then\n";
    # Claude CLI on Windows needs a clean Windows path (no mixed separators)
    print $fh "  GIT_BASH=\$(cygpath -w \"\$GIT_BASH\" 2>/dev/null || echo \"\$GIT_BASH\")\n";
    print $fh "  export CLAUDE_CODE_GIT_BASH_PATH=\"\$GIT_BASH\"\n";
    print $fh "fi\n\n";

    print $fh "cd \"$ROOT\"\n\n";

    # Write PID file for recovery daemon's job-specific process detection
    print $fh "echo \$\$ > \"$output_dir/pipeline.pid\"\n\n";

    # Orphan cleanup function: Claude CLIs with --dangerously-skip-permissions can
    # spawn child processes (e.g. pdfplumber) that survive after the parent exits.
    # This function kills any orphaned python.exe children spawned by our CLIs.
    print $fh "# --- Orphan process cleanup ---\n";
    print $fh "# Claude CLI can spawn python/pdfplumber subprocesses that outlive the parent.\n";
    print $fh "# Track PIDs per wave and kill stragglers after wait completes.\n";
    print $fh "WAVE_PIDS=\"\"\n";
    print $fh "cleanup_wave() {\n";
    print $fh "  for pid in \$WAVE_PIDS; do\n";
    print $fh "    # Kill the process tree rooted at each background PID\n";
    print $fh "    if kill -0 \$pid 2>/dev/null; then\n";
    print $fh "      echo \"Cleaning up orphaned process tree for PID \$pid\"\n";
    print $fh "      # Get all descendants via procps or taskkill\n";
    print $fh "      taskkill //PID \$pid //T //F > /dev/null 2>&1\n";
    print $fh "    fi\n";
    print $fh "  done\n";
    print $fh "  WAVE_PIDS=\"\"\n";
    print $fh "}\n";
    print $fh "trap 'cleanup_wave' EXIT\n\n";

    # Python discovery (Step 7)
    print $fh "# --- Python discovery ---\n";
    print $fh "PYUSER=\"\${USERNAME:-\$USER}\"\n";
    print $fh "PYTHON=\"\"\n";
    print $fh "for p in \\\n";
    print $fh "  \"/c/Users/\$PYUSER/AppData/Local/Programs/Python/Python313/python.exe\" \\\n";
    print $fh "  \"/c/Users/\$PYUSER/AppData/Local/Programs/Python/Python312/python.exe\" \\\n";
    print $fh "  \"/c/Users/\$PYUSER/AppData/Local/Programs/Python/Python311/python.exe\" \\\n";
    print $fh "  \"/c/Python313/python.exe\" \"/c/Python312/python.exe\" \\\n";
    print $fh "  \"\$(command -v python3 2>/dev/null)\" \\\n";
    print $fh "  \"\$(command -v python 2>/dev/null)\" \\\n";
    print $fh "  \"\$(command -v py 2>/dev/null)\"; do\n";
    print $fh "  [ -n \"\$p\" ] && [ -x \"\$p\" ] && { PYTHON=\"\$p\"; break; }\n";
    print $fh "done\n";
    print $fh "if [ -z \"\$PYTHON\" ]; then\n";
    print $fh "  echo \"ERROR: Python not found. Install Python 3.11+ and ensure it is on PATH.\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n";
    print $fh "echo \"Using Python: \$PYTHON\"\n";
    print $fh "\"\$PYTHON\" -m pip install --quiet openpyxl python-docx pdfplumber 2>/dev/null\n\n";

    # Phase 0: One-time PDF text extraction
    print $fh "# === PHASE 0: One-time PDF text extraction ===\n";
    print $fh "echo \"Phase 0: Extracting PDF text...\" >> \"$output_dir/progress.log\"\n";
    print $fh "\"\$PYTHON\" \"$ROOT/extract_pdf.py\" \"$job_dir/input.pdf\" \"$job_dir/pages\"\n";
    print $fh "if [ \$? -ne 0 ]; then\n";
    print $fh "  echo \"ERROR: extract_pdf.py failed. Check that pdfplumber is installed.\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n";
    print $fh "echo \"Phase 0 complete.\" >> \"$output_dir/progress.log\"\n\n";

    # Phase 1: parallel discipline CLIs (all 8 run simultaneously — API-bound, not CPU-bound)
    # Wave priority kept for ordering; with MAX_PARALLEL=8, all fit in a single wave.
    my %wave_priority = (
        'communications' => 1,   # Wave 1 - slow (399KB standards)
        'plumbing'       => 1,   # Wave 1 - fast (49KB)
        'fire-protection' => 1,  # Wave 1 - fast (57KB)
        'civil-site'     => 2,   # Wave 2 - slow (281KB)
        'arch-finishes'  => 2,   # Wave 2 - fast (91KB)
        'electrical'     => 2,   # Wave 2 - medium (100KB)
        'hvac-controls'  => 3,   # Wave 3 - medium (196KB)
        'arch-structure'  => 3,  # Wave 3 - medium (163KB)
    );
    my $MAX_PARALLEL = 8;  # all disciplines run simultaneously (API-bound, not CPU-bound)

    # Sort @active into waves based on priority (unrecognized keys go to last wave)
    my @sorted = sort { ($wave_priority{$a->{key}} || 99) <=> ($wave_priority{$b->{key}} || 99) } @active;

    # Chunk into waves of MAX_PARALLEL
    my @waves;
    while (@sorted) {
        push @waves, [ splice @sorted, 0, $MAX_PARALLEL ];
    }
    my $num_waves = scalar @waves;

    print $fh "# === PHASE 1: $expected_count parallel discipline scans ===\n";
    print $fh "echo \"Phase 1: Launching $expected_count discipline scans (all parallel)...\" >> \"$output_dir/progress.log\"\n\n";

    for my $wi (0 .. $#waves) {
        my $wave = $waves[$wi];
        my $wave_num = $wi + 1;
        my $wave_count = scalar @$wave;
        my $wave_names = join(', ', map { $_->{name} } @$wave);

        print $fh "# --- Batch $wave_num of $num_waves ($wave_count disciplines: $wave_names) ---\n";
        print $fh "WAVE_PIDS=\"\"\n";
        print $fh "echo \"Launching $wave_count disciplines: $wave_names\"\n";
        print $fh "echo \"Launching: $wave_names\" >> \"$output_dir/progress.log\"\n\n";

        for my $grp (@$wave) {
            my $pfile   = "$job_dir/prompt-$grp->{key}.txt";
            my $stdout  = "$output_dir/$grp->{key}-stdout.log";
            my $stderr  = "$output_dir/$grp->{key}-stderr.log";

            (my $var_key = uc($grp->{key})) =~ s/-/_/g;  # bash-safe var name
            print $fh "# Discipline: $grp->{name}\n";
            print $fh "echo \"  Launching: $grp->{name}...\"\n";
            print $fh "PROMPT_${var_key}=\$(cat \"$pfile\")\n";
            print $fh "\"$CLAUDE_PATH\" -p \"\$PROMPT_${var_key}\" \\\n";
            print $fh "  --model sonnet \\\n";
            print $fh "  --allowedTools Read Write \\\n";
            print $fh "  --dangerously-skip-permissions \\\n";
            print $fh "  --output-format text \\\n";
            print $fh "  > \"$stdout\" \\\n";
            print $fh "  2> \"$stderr\" &\n";
            print $fh "WAVE_PIDS=\"\$WAVE_PIDS \$!\"\n\n";
        }

        print $fh "# Wait for batch $wave_num to complete, then kill orphaned children\n";
        print $fh "echo \"Waiting for $wave_count disciplines...\"\n";
        print $fh "wait\n";
        print $fh "cleanup_wave\n";
        print $fh "echo \"Batch $wave_num/$num_waves complete.\" >> \"$output_dir/progress.log\"\n\n";
    }

    print $fh "echo \"Phase 1 complete ($expected_count disciplines).\" >> \"$output_dir/progress.log\"\n\n";

    # Validate Phase 1 output
    print $fh "# Validate Phase 1 output\n";
    print $fh "FOUND=0\n";
    print $fh "for f in \"$output_dir\"/discipline-*-findings.json; do\n";
    print $fh "  [ -f \"\$f\" ] && FOUND=\$((FOUND + 1))\n";
    print $fh "done\n";
    print $fh "echo \"Phase 1 produced \$FOUND of $expected_count findings files.\"\n";
    print $fh "if [ \"\$FOUND\" -lt 1 ]; then\n";
    print $fh "  echo \"ERROR: No discipline findings JSON files produced. Check stderr logs.\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n\n";

    # Phase 2a: Python synthesis (JSON merge + renumber, zero tokens)
    print $fh "# === PHASE 2a: Python synthesis -> review-data.json ===\n";
    print $fh "echo \"Phase 2a: Synthesizing (Python)...\" >> \"$output_dir/progress.log\"\n";
    my $synth_stdout = "$output_dir/synthesis-stdout.log";
    my $synth_stderr = "$output_dir/synthesis-stderr.log";
    print $fh "\"\$PYTHON\" \"$ROOT/synthesize.py\" \"$output_dir\" \\\n";
    print $fh "  > \"$synth_stdout\" \\\n";
    print $fh "  2> \"$synth_stderr\"\n\n";

    print $fh "if [ ! -f \"$output_dir/review-data.json\" ]; then\n";
    print $fh "  echo \"ERROR: synthesize.py did not produce review-data.json. Check synthesis-stderr.log\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n";
    print $fh "echo \"Phase 2a complete: review-data.json produced.\" >> \"$output_dir/progress.log\"\n\n";

    # Phase 2b: Claude executive summary (Haiku, small + fast)
    my $exec_prompt = "$job_dir/prompt-exec-summary.txt";
    my $exec_stdout = "$output_dir/executive-summary.txt";
    my $exec_stderr = "$output_dir/summary-stderr.log";
    print $fh "# === PHASE 2b: Claude executive summary (Haiku) ===\n";
    print $fh "echo \"Phase 2b: Generating executive summary...\" >> \"$output_dir/progress.log\"\n";
    print $fh "EXEC_PROMPT=\$(cat \"$exec_prompt\")\n";
    print $fh "cd \"$output_dir\"\n";
    print $fh "\"$CLAUDE_PATH\" -p \"\$EXEC_PROMPT\" \\\n";
    print $fh "  --model haiku \\\n";
    print $fh "  --allowedTools Read Write \\\n";
    print $fh "  --dangerously-skip-permissions \\\n";
    print $fh "  --output-format text \\\n";
    print $fh "  > \"$exec_stdout\" \\\n";
    print $fh "  2> \"$exec_stderr\"\n";
    print $fh "cd \"$ROOT\"\n";
    print $fh "echo \"Phase 2b complete.\" >> \"$output_dir/progress.log\"\n\n";

    # Phase 3: local Python report generation
    print $fh "# === PHASE 3: Local report generation (zero tokens) ===\n";
    print $fh "echo \"Phase 3: Generating reports...\" >> \"$output_dir/progress.log\"\n";
    print $fh "\"\$PYTHON\" \"$ROOT/generate_reports.py\" \"$output_dir/review-data.json\"\n";
    print $fh "PYEXIT=\$?\n";
    print $fh "if [ \"\$PYEXIT\" -ne 0 ]; then\n";
    print $fh "  echo \"ERROR: generate_reports.py failed (exit code \$PYEXIT)\" >> \"$output_dir/progress.log\"\n";
    print $fh "  # FAILED file already written by generate_reports.py if validation failed\n";
    print $fh "  [ ! -f \"$output_dir/FAILED\" ] && echo \"generate_reports.py exited with code \$PYEXIT\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n\n";

    print $fh "echo \"Pipeline complete.\" >> \"$output_dir/progress.log\"\n";

    close $fh;
    chmod 0755, $script;

    my $group_names = join(', ', map { $_->{name} } @active);
    print "[" . localtime() . "] Spawning pipeline for job $job_id\n";
    print "  Phase 1:  " . scalar(@active) . " CLIs, all parallel (Sonnet) -> JSON\n";
    print "  Phase 2a: Python synthesis -> review-data.json\n";
    print "  Phase 2b: Claude Haiku -> executive-summary.txt\n";
    print "  Phase 3:  Local Python -> reports\n";
    print "  Groups: $group_names\n";
    print "  Script: $script\n";
    # Write a tiny launcher that nohup's the main script in background.
    # MSYS Perl's system() goes through cmd.exe which doesn't support &,
    # so we create a launcher script that bash can run and background properly.
    (my $script_bash = $script) =~ s{\\}{/}g;
    my $launcher = "$job_dir/launch.sh";
    open my $lfh, '>', $launcher or do {
        warn "Cannot write launcher: $!\n";
        return;
    };
    print $lfh "#!/bin/bash\n";
    print $lfh "nohup bash \"$script_bash\" > /dev/null 2>&1 &\n";
    close $lfh;
    chmod 0755, $launcher;
    system("bash \"$launcher\"");
}

# --- Request handler --------------------------------------------------------

while (my $c = $srv->accept) {
    binmode $c;

    # 30-second timeout for initial request read (prevents dead connections from blocking)
    my $sel = IO::Select->new($c);
    unless ($sel->can_read(30)) {
        close $c;
        next;
    }

    # Read request line
    my $req_line = <$c>;
    next unless $req_line && $req_line =~ m{^(GET|POST|DELETE|OPTIONS)\s+(/\S*)\s+HTTP};
    my ($method, $path) = ($1, $2);
    $path =~ s/\?.*//;  # strip query string

    # Read all headers
    my %headers;
    my $header_ok = 1;
    while (1) {
        my $hdr = <$c>;
        unless (defined $hdr) { $header_ok = 0; last; }
        $hdr =~ s/\r?\n$//;
        last if $hdr eq '';
        if ($hdr =~ /^([^:]+):\s*(.*)/) {
            $headers{lc $1} = $2;
        }
    }
    unless ($header_ok) {
        close $c;
        next;
    }
    # CORS preflight
    if ($method eq 'OPTIONS') {
        print $c "HTTP/1.0 204 No Content\r\n"
            . "Access-Control-Allow-Origin: *\r\n"
            . "Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS\r\n"
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

        # Concurrent job guard: prevent submitting while another review is running
        {
            my $running_id;
            if (opendir my $dh, $REVIEWS_DIR) {
                while (my $dir = readdir $dh) {
                    next if $dir =~ /^\./;
                    my $existing = read_job_json($dir);
                    if ($existing && ($existing->{status} || '') eq 'Processing') {
                        $running_id = $dir;
                        last;
                    }
                }
                closedir $dh;
            }
            if ($running_id) {
                send_json($c, 409, {
                    error => "A review is already running (job $running_id). Please wait for it to complete before submitting another.",
                    runningJob => $running_id,
                });
                close $c;
                next;
            }
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

    # GET /api/jobs — list all jobs (wrapped with stats)
    if ($method eq 'GET' && $path eq '/api/jobs') {
        my @jobs;
        my $total_bytes = 0;
        if (opendir my $dh, $REVIEWS_DIR) {
            while (my $dir = readdir $dh) {
                next if $dir =~ /^\./;
                my $j = check_job_status($dir);
                if ($j) {
                    push @jobs, $j;
                    # Sum file sizes (2 levels: job dir + output/ + combined/)
                    my $job_path = "$REVIEWS_DIR/$dir";
                    for my $subdir ($job_path, "$job_path/output", "$job_path/combined") {
                        if (opendir my $sdh, $subdir) {
                            for my $f (readdir $sdh) {
                                next if $f =~ /^\./;
                                my $sz = (stat "$subdir/$f")[7] || 0;
                                $total_bytes += $sz;
                            }
                            closedir $sdh;
                        }
                    }
                }
            }
            closedir $dh;
        }
        @jobs = sort { ($b->{submitted} || '') cmp ($a->{submitted} || '') } @jobs;
        send_json($c, 200, {
            jobs       => \@jobs,
            totalJobs  => scalar @jobs,
            totalBytes => $total_bytes,
        });
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

    # DELETE /api/jobs/{id} — delete a job and all its files
    if ($method eq 'DELETE' && $path =~ m{^/api/jobs/([a-zA-Z0-9_-]+)$}) {
        my $id = $1;
        my $job_dir = "$REVIEWS_DIR/$id";
        if (-f "$job_dir/job.json") {
            remove_tree($job_dir);
            print "[" . localtime() . "] Deleted job $id\n";
            send_json($c, 200, { deleted => $id });
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

    # GET /api/logs/{id}/{filename} — serve log/txt files from output dir
    if ($method eq 'GET' && $path =~ m{^/api/logs/([a-zA-Z0-9_-]+)/([a-zA-Z0-9._-]+)$}) {
        my ($id, $filename) = ($1, $2);
        $filename =~ s/[^a-zA-Z0-9._-]//g;  # sanitize
        # Restrict to .log and .txt files only (security)
        if ($filename !~ /\.(log|txt)$/) {
            send_json($c, 400, { error => 'Only .log and .txt files can be downloaded' });
            close $c; next;
        }
        my $file = "$REVIEWS_DIR/$id/output/$filename";
        if (-f $file) {
            open my $fh, '<:raw', $file or do {
                send_json($c, 500, { error => 'Cannot read file' });
                close $c; next;
            };
            local $/; my $data = <$fh>; close $fh;
            send_response($c, 200, 'text/plain', $data);
        } else {
            send_json($c, 404, { error => 'Log file not found' });
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
