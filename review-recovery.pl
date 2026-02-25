#!/usr/bin/perl
# review-recovery.pl — Recovery daemon for stalled WSU compliance review jobs.
# Watches the reviews/ directory for stuck jobs and kicks them back into gear
# WITHOUT spending API tokens. Primary action: re-run Phase 3 (local Python)
# when review-data.json exists but deliverables are missing/incomplete.
#
# Usage: perl review-recovery.pl
#   Runs as a background daemon, polling every 2 minutes.
#   Press Ctrl+C to stop.

use strict;
use warnings;
use File::Basename;
use Cwd 'abs_path';
use JSON::PP;

my $ROOT        = dirname(abs_path($0));
my $REVIEWS_DIR = "$ROOT/reviews";

# --- Configuration ---
my $POLL_INTERVAL   = 120;     # seconds between scans
my $STALL_THRESHOLD = 15;      # minutes idle before considering stalled
my $DEAD_THRESHOLD  = 30;      # minutes idle before declaring dead
my $MAX_PY_RETRIES  = 3;       # max Phase 3 re-runs per job
my $LOG_FILE        = "$ROOT/recovery.log";

# --- Helpers (shared patterns from review-server.pl) ---

sub iso_now {
    my @t = localtime;
    return sprintf('%04d-%02d-%02dT%02d:%02d:%02d',
        $t[5]+1900, $t[4]+1, $t[3], $t[2], $t[1], $t[0]);
}

sub log_action {
    my ($job_id, $tag, $msg) = @_;
    my $ts = iso_now();
    my $line = "[$ts] [$job_id] [$tag] $msg\n";
    print $line;
    if (open my $fh, '>>', $LOG_FILE) {
        print $fh $line;
        close $fh;
    }
}

sub write_file {
    my ($path, $content) = @_;
    open my $fh, '>', $path or do {
        warn "Cannot write $path: $!\n";
        return;
    };
    print $fh $content;
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

# --- Python discovery (same pattern as run-review.sh) ---

sub find_python {
    my $user = $ENV{USERNAME} || $ENV{USER} || '';
    for my $p (
        "C:/Users/$user/AppData/Local/Programs/Python/Python313/python.exe",
        "C:/Users/$user/AppData/Local/Programs/Python/Python312/python.exe",
        "C:/Users/$user/AppData/Local/Programs/Python/Python311/python.exe",
        "C:/Python313/python.exe",
        "C:/Python312/python.exe",
    ) {
        return $p if -f $p && -x $p;
    }
    # Try PATH
    my $which = `where python 2>nul`;
    chomp $which;
    # where can return multiple lines; take first
    ($which) = split(/\n/, $which);
    $which = '' unless $which && -f $which;
    return $which;
}

# --- Retry tracking ---

sub read_retry_count {
    my ($job_id) = @_;
    my $f = "$REVIEWS_DIR/$job_id/output/recovery-retries.txt";
    return 0 unless -f $f;
    open my $fh, '<', $f or return 0;
    my $n = <$fh>;
    chomp $n if defined $n;
    close $fh;
    return int($n || 0);
}

sub increment_retry_count {
    my ($job_id) = @_;
    my $n = read_retry_count($job_id) + 1;
    write_file("$REVIEWS_DIR/$job_id/output/recovery-retries.txt", "$n\n");
}

# --- Stall detection ---

sub get_newest_mtime {
    my ($outdir) = @_;
    my $newest = 0;
    opendir my $dh, $outdir or return 0;
    for my $f (readdir $dh) {
        next if $f =~ /^\./;
        my $mt = (stat "$outdir/$f")[9] || 0;
        $newest = $mt if $mt > $newest;
    }
    closedir $dh;
    return $newest;
}

sub idle_minutes {
    my ($outdir) = @_;
    my $newest = get_newest_mtime($outdir);
    return 999 unless $newest > 0;  # No files = very stale
    return (time() - $newest) / 60;
}

# --- Phase detection ---

sub detect_phase {
    my ($job_id, $job) = @_;
    my $outdir = "$REVIEWS_DIR/$job_id/output";

    # Phase 3: review-data.json exists
    return 3 if -f "$outdir/review-data.json";

    # Phase 2: synthesis started
    return 2 if -f "$outdir/synthesis-stdout.log";

    # Count discipline findings
    my $expected = $job->{expectedGroups} || 0;
    my @jsons = glob("$outdir/discipline-*-findings.json");
    my @mds   = glob("$outdir/discipline-*-findings.md");
    my $found = scalar(@jsons) + scalar(@mds);

    # All disciplines done → should be in Phase 2
    return 2 if $found >= $expected && $expected > 0;

    # Some disciplines done → Phase 1 in progress
    return 1 if $found > 0;

    # Nothing yet → Phase 1 (just submitted)
    return 1;
}

# --- Process liveness ---

sub has_active_processes {
    my ($job_id) = @_;

    # Job-specific detection: check PID file written by run-review.sh
    if ($job_id) {
        my $pidfile = "$REVIEWS_DIR/$job_id/output/pipeline.pid";
        if (-f $pidfile) {
            open my $fh, '<', $pidfile or goto FALLBACK;
            my $pid = <$fh>;
            chomp $pid if defined $pid;
            close $fh;
            if ($pid && $pid =~ /^\d+$/) {
                # Check if that specific PID is still alive
                my $check = `tasklist /FI "PID eq $pid" /FO CSV 2>nul`;
                return 1 if $check =~ /"\Q$pid\E"/;
                # PID is dead — pipeline finished or crashed
                return 0;
            }
        }
    }

    FALLBACK:
    # Fallback: global heuristic (backward compatibility for jobs without PID file)
    my $claude_out = `tasklist /FI "IMAGENAME eq claude.exe" /FO CSV 2>nul`;
    my $python_out = `tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul`;

    my $claude_running = ($claude_out =~ /claude\.exe/i)  ? 1 : 0;
    my $python_running = ($python_out =~ /python\.exe/i)  ? 1 : 0;

    return ($claude_running || $python_running);
}

# --- Zero-byte cleanup ---

sub cleanup_zero_byte_files {
    my ($job_id) = @_;
    my $outdir = "$REVIEWS_DIR/$job_id/output";
    my $cleaned = 0;

    # Discipline JSON files
    for my $f (glob("$outdir/discipline-*-findings.json")) {
        if (-f $f && (-s $f || 0) == 0) {
            unlink $f;
            log_action($job_id, "CLEANED", "Deleted 0-byte: " . basename($f));
            $cleaned++;
        }
    }

    # review-data.json
    my $rdj = "$outdir/review-data.json";
    if (-f $rdj && (-s $rdj || 0) == 0) {
        unlink $rdj;
        log_action($job_id, "CLEANED", "Deleted 0-byte review-data.json");
        $cleaned++;
    }

    return $cleaned;
}

# --- Phase 3 recovery ---

sub is_phase3_failure {
    my ($outdir) = @_;
    my $failed = "$outdir/FAILED";
    return 0 unless -f $failed;

    # If review-data.json exists, it's necessarily a Phase 3 failure
    # (Phases 1 & 2 completed successfully to produce it)
    return 1 if -f "$outdir/review-data.json" && -s "$outdir/review-data.json";

    # Fallback: check FAILED file content for Phase 3 keywords
    open my $fh, '<', $failed or return 0;
    local $/;
    my $content = <$fh>;
    close $fh;

    # Exclude if explicitly a Phase 1 or Phase 2 failure
    return 0 if $content =~ /Phase 1/i;
    return 0 if $content =~ /Phase 2/i;
    return 0 if $content =~ /No discipline findings/i;
    return 0 if $content =~ /synthesize\.py/i;

    # Match known Phase 3 patterns (Python/report generation)
    return 1 if $content =~ /generate_reports\.py/i;
    return 1 if $content =~ /REPORT GENERATION FAILED/i;
    return 1 if $content =~ /NUMBER VALIDATION FAILED/i;
    return 1 if $content =~ /openpyxl/i;
    return 1 if $content =~ /python-docx/i;
    return 1 if $content =~ /Traceback/i;
    return 1 if $content =~ /ModuleNotFoundError/i;
    return 1 if $content =~ /ImportError/i;
    return 1 if $content =~ /PermissionError/i;
    return 1 if $content =~ /FileNotFoundError/i;
    return 0;
}

sub recover_phase3 {
    my ($job_id, $outdir) = @_;

    # Increment retry count FIRST — ensures counter advances even if validation fails,
    # preventing infinite retry loops on permanently bad data
    increment_retry_count($job_id);
    my $retries = read_retry_count($job_id);

    # Check retry count
    if ($retries > $MAX_PY_RETRIES) {
        write_file("$outdir/FAILED",
            "Recovery daemon: Phase 3 failed after $MAX_PY_RETRIES retries. "
            . "Check review-data.json manually or re-submit.");
        log_action($job_id, "EXHAUSTED",
            "Phase 3 retries exhausted ($retries/$MAX_PY_RETRIES)");
        return;
    }

    # Validate review-data.json is non-empty
    my $rdj = "$outdir/review-data.json";
    my $size = -s $rdj || 0;
    if ($size == 0) {
        unlink $rdj;
        log_action($job_id, "CLEANED",
            "Deleted 0-byte review-data.json — needs Phase 2 re-run (tokens required)");
        return;
    }

    # Validate it's parseable JSON
    if (open my $fh, '<', $rdj) {
        local $/;
        my $content = <$fh>;
        close $fh;
        my $parsed = eval { decode_json($content) };
        if (!$parsed) {
            log_action($job_id, "BAD_JSON",
                "review-data.json is not valid JSON — cannot recover");
            write_file("$outdir/FAILED",
                "Recovery daemon: review-data.json is corrupt/invalid JSON. Re-submit.");
            return;
        }
    }

    # Clean up existing FAILED file (we're retrying)
    unlink "$outdir/FAILED" if -f "$outdir/FAILED";

    # Clean up partial deliverables (Python regenerates all)
    for my $f (qw(report.docx report.xlsx checklist.txt findings.txt notes.txt COMPLETE)) {
        if (-f "$outdir/$f") {
            unlink "$outdir/$f";
            log_action($job_id, "CLEANED", "Deleted partial: $f");
        }
    }

    # Discover Python
    my $python = find_python();
    if (!$python) {
        write_file("$outdir/FAILED",
            "Recovery daemon: Python not found. Install Python 3.11+ and add to PATH.");
        log_action($job_id, "NO_PYTHON", "Cannot recover — Python not installed");
        return;
    }

    # Re-run Phase 3
    log_action($job_id, "RETRY",
        "Re-running Phase 3 (attempt $retries/$MAX_PY_RETRIES) using $python");

    # Normalize paths for bash
    (my $py_bash = $python) =~ s{\\}{/}g;
    (my $gen_bash = "$ROOT/generate_reports.py") =~ s{\\}{/}g;
    (my $rdj_bash = $rdj) =~ s{\\}{/}g;
    (my $out_bash = "$outdir/recovery-stdout.log") =~ s{\\}{/}g;

    # Run in background so daemon doesn't block
    my $cmd = qq{bash -c '"$py_bash" "$gen_bash" "$rdj_bash" >> "$out_bash" 2>&1' &};
    system($cmd);
}

# --- Main analysis per job ---

sub analyze_and_recover {
    my ($job_id, $job) = @_;
    my $outdir = "$REVIEWS_DIR/$job_id/output";

    # Always clean up zero-byte files
    cleanup_zero_byte_files($job_id);

    my $phase = detect_phase($job_id, $job);
    my $idle  = idle_minutes($outdir);

    # Check for Phase 3 FAILED that we can retry
    if ($phase == 3 && -f "$outdir/FAILED" && is_phase3_failure($outdir)) {
        my $has_procs = has_active_processes($job_id);
        if (!$has_procs) {
            log_action($job_id, "DETECTED",
                "Phase 3 failure detected (idle ${idle}min), attempting recovery");
            recover_phase3($job_id, $outdir);
        }
        return;
    }

    # Not stalled yet? Skip.
    return if $idle < $STALL_THRESHOLD;

    my $has_procs = has_active_processes($job_id);

    # If processes are running and we're under the dead threshold, give more time
    return if $has_procs && $idle < $DEAD_THRESHOLD;

    my $idle_str = sprintf("%.0f", $idle);

    # --- Phase 3 recovery (zero tokens) ---
    if ($phase == 3 && !-f "$outdir/FAILED") {
        log_action($job_id, "DETECTED",
            "Phase 3 stalled (idle ${idle_str}min, no sentinel), attempting recovery");
        recover_phase3($job_id, $outdir);
        return;
    }

    # --- Phase 1/2 stall (can't fix without tokens) ---
    if ($idle >= $DEAD_THRESHOLD && !$has_procs) {
        my $phase_name = $phase == 1 ? "Phase 1 (discipline scans)"
                       : $phase == 2 ? "Phase 2 (synthesis)"
                       : "Phase $phase";
        my $msg = "Recovery daemon: Job stalled in $phase_name for ${idle_str} minutes "
                . "with no active processes. Re-submit through the portal to restart.";
        write_file("$outdir/FAILED", $msg);
        log_action($job_id, "DEAD",
            "$phase_name dead — no processes, idle ${idle_str}min. Wrote FAILED.");
    }
}

# --- Job scanner ---

sub scan_jobs {
    return unless -d $REVIEWS_DIR;
    opendir my $dh, $REVIEWS_DIR or do {
        log_action("SYSTEM", "ERROR", "Cannot open $REVIEWS_DIR: $!");
        return;
    };
    my @dirs = sort grep { /^\d{8}-\d{6}$/ && -d "$REVIEWS_DIR/$_" } readdir $dh;
    closedir $dh;

    for my $job_id (@dirs) {
        my $job = read_job_json($job_id);
        next unless $job;

        # Only look at Processing jobs
        my $status = $job->{status} || '';
        next unless $status eq 'Processing';

        my $outdir = "$REVIEWS_DIR/$job_id/output";
        next unless -d $outdir;

        # Skip if already has COMPLETE sentinel
        next if -f "$outdir/COMPLETE";

        # FAILED is special: we skip it UNLESS it's a Phase 3 failure we can retry
        if (-f "$outdir/FAILED") {
            if (is_phase3_failure($outdir)) {
                # Might be recoverable — let analyze_and_recover handle it
            } else {
                next;  # Non-Phase-3 failure, nothing we can do
            }
        }

        analyze_and_recover($job_id, $job);
    }
}

# --- Main ---

print "=" x 50 . "\n";
print "  WSU Review Recovery Daemon\n";
print "=" x 50 . "\n";
print "  Reviews:     $REVIEWS_DIR\n";
print "  Log file:    $LOG_FILE\n";
print "  Poll:        every ${POLL_INTERVAL}s\n";
print "  Stall:       ${STALL_THRESHOLD}min\n";
print "  Dead:        ${DEAD_THRESHOLD}min\n";
print "  Max retries: $MAX_PY_RETRIES\n";

my $python = find_python();
if ($python) {
    print "  Python:      $python\n";
} else {
    print "  Python:      NOT FOUND (Phase 3 recovery disabled until installed)\n";
}
print "\n";

log_action("SYSTEM", "START", "Recovery daemon started");

while (1) {
    eval { scan_jobs() };
    if ($@) {
        log_action("SYSTEM", "ERROR", "Scan failed: $@");
    }
    sleep $POLL_INTERVAL;
}
