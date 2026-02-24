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
        # Estimate progress from milestone files
        my $pct = 5;  # Submitted
        $pct = 15  if -f "$job_dir/extracted.txt" || -f "$job_dir/extracted-layout.txt"
                    || -f "$job_dir/input.txt";
        $pct = 30  if -f "$job_dir/output/checklist.md";
        $pct = 50  if -f "$job_dir/output/findings.md";
        $pct = 65  if -f "$job_dir/output/notes.md";
        $pct = 75  if -f "$job_dir/output/report.docx" || -f "$job_dir/output/report-word.md";
        $pct = 85  if -f "$job_dir/output/report.pptx" || -f "$job_dir/output/report-ppt.md";
        $pct = 95  if (-f "$job_dir/output/report.docx" || -f "$job_dir/output/report-word.md")
                    && (-f "$job_dir/output/report.pptx" || -f "$job_dir/output/report-ppt.md");
        $job->{progress} = $pct;
    }
    return $job;
}

# --- Spawn Claude -----------------------------------------------------------

sub spawn_review {
    my ($job_id, $job) = @_;
    my $output_dir = "$REVIEWS_DIR/$job_id/output";
    make_path($output_dir) unless -d $output_dir;

    my $divs = join(', ', @{$job->{divisions} || []});
    my $prompt = "Process compliance review job $job_id. "
        . "Read the PDF at reviews/$job_id/input.pdf. "
        . "Project: $job->{projectName}. "
        . "Divisions: $divs. "
        . "Phase: $job->{reviewPhase}. "
        . "Construction type: $job->{constructionType}. "
        . "Follow the wsu-compliance-review workflow. "
        . "Read standards/INDEX.md first. "
        . "Write checklist.md, findings.md, and notes.md to reviews/$job_id/output/. "
        . "Also generate a Word document (report.docx) and a PowerPoint presentation (report.pptx) "
        . "in reviews/$job_id/output/ using python-docx and python-pptx (pip install if needed). "
        . "CITATION REQUIREMENTS: Every finding MUST include two specific citations: "
        . "(1) PDF page number where the issue appears (e.g., 'PDF p.12, Sheet E-101'), "
        . "(2) the WSU standard section number (e.g., 'WSU 26-24-00, Section 3.02.A'). "
        . "Carry these citations into the Word and PowerPoint reports as well. "
        . "Create reviews/$job_id/output/COMPLETE when all outputs are written. "
        . "If you encounter an error, create reviews/$job_id/output/FAILED with the error description.";

    # Escape single quotes for bash script
    $prompt =~ s/'/'\\''/g;

    my $job_dir    = "$REVIEWS_DIR/$job_id";
    my $stdout_log = "$output_dir/claude-stdout.log";
    my $stderr_log = "$output_dir/claude-stderr.log";
    my $script     = "$job_dir/run-review.sh";

    # Write a shell wrapper script — avoids MSYS Perl system() parsing issues
    open my $fh, '>', $script or do {
        warn "Cannot write $script: $!\n";
        return;
    };
    print $fh <<BASH;
#!/bin/bash
unset CLAUDECODE
export CLAUDE_CODE_GIT_BASH_PATH='C:\\Users\\john.slagboom\\AppData\\Local\\Programs\\Git\\bin\\bash.exe'
cd "$ROOT"
"$CLAUDE_PATH" -p '$prompt' \\
  --dangerously-skip-permissions \\
  --output-format text \\
  > "$stdout_log" \\
  2> "$stderr_log"
BASH
    close $fh;
    chmod 0755, $script;

    print "[" . localtime() . "] Spawning Claude for job $job_id\n";
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
