#!/usr/bin/perl
# split-standards.pl — Split WSU-DESIGN-STANDARDS-COMPLETE.txt into per-section Markdown files.
# Usage: perl split-standards.pl <input.txt> <output-dir>
#
# Reads the monolithic standards file, splits on === HEADER === delimiters,
# routes each section to the correct division folder, resolves duplicates
# (newest date wins), and writes a manifest for index generation.

use strict;
use warnings;
use File::Path qw(make_path);
use File::Basename;

my $INPUT  = shift or die "Usage: $0 <input.txt> <output-dir>\n";
my $OUTDIR = shift || 'standards/wsu';

my $MAX_LINES = 1500;

# Track duplicates: csi_code => [ { date, path, title, line_start, line_count } ]
my %csi_versions;

# Manifest for index generation
my @manifest;

# State
my $current_fh;
my $current_path;
my $current_title;
my $current_csi;
my $current_date;
my $current_category;  # standard | campus-wide | supplemental | detail-drawing
my $current_lines = 0;
my $current_start_line = 0;
my $in_supplemental = 0;
my $in_detail_drawings = 0;
my $line_num = 0;
my $skip_header = 1;  # skip file header until first section

open my $fh, '<:raw', $INPUT or die "Cannot open $INPUT: $!\n";

while (my $line = <$fh>) {
    $line_num++;
    chomp $line;

    # Skip pure separator lines
    next if $line =~ /^={10,}$/;

    # Detect supplemental marker
    if ($line =~ /^=== SUPPLEMENTAL DOCUMENTS/) {
        $in_supplemental = 1;
        close_section();
        next;
    }

    # Detect section headers
    if ($line =~ /^=== (.+?) ===\s*$/) {
        my $header = $1;
        close_section();
        $skip_header = 0;

        # Parse the header
        my ($csi, $title, $date, $category) = parse_header($header);

        # Detect detail drawings (supplemental sections with hyphenated CSI-style names)
        if ($in_supplemental && $header =~ /^\d{2}-\d{2}-\d{2}/) {
            $in_detail_drawings = 1;
            $category = 'detail-drawing';
        }

        # Determine output path
        my $path = determine_path($csi, $title, $header, $category);

        # Open new file
        my $dir = dirname($path);
        make_path($dir) unless -d $dir;
        open $current_fh, '>:raw', $path or die "Cannot write $path: $!\n";
        $current_path  = $path;
        $current_title = $title || $header;
        $current_csi   = $csi || '';
        $current_date  = $date || '';
        $current_category = $category;
        $current_lines = 0;
        $current_start_line = $line_num;

        # Write metadata header
        my $display_title = $current_title;
        $display_title =~ s/_\d{8}$//;  # strip date suffix from title
        my $div_num = '';
        if ($csi && $csi =~ /^(\d{2})/) { $div_num = $1; }

        print $current_fh "# " . ($csi ? "CSI $csi - " : "") . "$display_title\n\n";
        print $current_fh "> **Division:** $div_num\n" if $div_num;
        print $current_fh "> **CSI Code:** $csi\n" if $csi;
        print $current_fh "> **Title:** $display_title\n";
        print $current_fh "> **Date:** $date\n" if $date;
        print $current_fh "> **Source:** WSU Facilities Services Design & Construction Standards (June 2025)\n";
        print $current_fh "> **Category:** $category\n" if $category ne 'standard';
        print $current_fh "\n---\n\n";
        $current_lines += 7;

        next;
    }

    # Skip file header lines before first section
    next if $skip_header;

    # Write content
    if ($current_fh) {
        print $current_fh "$line\n";
        $current_lines++;
    }
}

close_section();
close $fh;

# Resolve duplicates
resolve_duplicates();

# Split oversized files
split_oversized();

# Write manifest
write_manifest();

print "\nDone. Files written to $OUTDIR/\n";
print "Manifest: $OUTDIR/MANIFEST.txt\n";

# ============================================================================
sub close_section {
    return unless $current_fh;
    close $current_fh;

    # Record in csi_versions for duplicate tracking
    if ($current_csi) {
        push @{$csi_versions{$current_csi}}, {
            date  => $current_date,
            path  => $current_path,
            title => $current_title,
            lines => $current_lines,
        };
    }

    # Record in manifest
    push @manifest, {
        csi      => $current_csi,
        title    => $current_title,
        date     => $current_date,
        path     => $current_path,
        lines    => $current_lines,
        category => $current_category,
    };

    $current_fh = undef;
}

# ============================================================================
sub parse_header {
    my ($header) = @_;
    my ($csi, $title, $date);
    my $category = 'standard';

    # Pattern 1: CSI code with spaces (e.g., "02 40 00", "22 06 10 13")
    if ($header =~ /^(\d{2}\s\d{2}\s\d{2}(?:\s\d{2})?)\s*[-]?\s*(.+)/) {
        $csi = $1;
        $title = $2;
    }
    # Pattern 2: CSI code with leading "25 50 00 - " dash separator
    elsif ($header =~ /^(\d{2} \d{2} \d{2})\s*-\s*(.+)/) {
        $csi = $1;
        $title = $2;
    }
    # Pattern 3: Year-prefixed campus-wide docs
    elsif ($header =~ /^(2024|2025)/) {
        $category = 'campus-wide';
        $title = $header;
    }
    # Pattern 4: "Final Contextual Aesthetic Booklet"
    elsif ($header =~ /^Final Contextual/) {
        $category = 'campus-wide';
        $title = $header;
    }
    # Pattern 5: Supplemental hyphenated names (27-audio-visual-design-guide)
    elsif ($header =~ /^\d{2}-/) {
        $category = $in_supplemental ? 'supplemental' : 'standard';
        $title = $header;
        # Extract pseudo-CSI from hyphenated name
        if ($header =~ /^(\d{2})-(\d{2})-(\d{2})/) {
            $csi = "$1 $2 $3";
            $category = $in_supplemental ? 'detail-drawing' : 'standard';
        } elsif ($header =~ /^(\d{2})-/) {
            # Just division-level (e.g., 27-audio-visual-design-guide)
            $category = 'supplemental';
        }
    }
    # Pattern 6: Supplemental appendix names (25-appendix-3-bas-point-naming)
    elsif ($in_supplemental) {
        $category = 'supplemental';
        $title = $header;
    }

    # Extract date from title
    if ($title) {
        # Pattern: _YYYYMMDD suffix
        if ($title =~ /_(\d{4})(\d{2})(\d{2})$/) {
            $date = "$1-$2-$3";
            $title =~ s/_\d{8}$//;
        }
        # Pattern: "as of M-DD-YY" or "as of MM-DD-YY"
        elsif ($title =~ /,?\s*as of\s+(.+)$/) {
            $date = $1;
            $title =~ s/,?\s*as of\s+.+$//;
        }
        # Pattern: "YYYY Report" or just year at end
        elsif ($title =~ /,?\s*(\d{1,2}-\d{1,2}-\d{2,4})$/) {
            $date = $1;
            $title =~ s/,?\s*\d{1,2}-\d{1,2}-\d{2,4}$//;
        }
        $title =~ s/\s+$//;
    }

    return ($csi, $title, $date, $category);
}

# ============================================================================
sub determine_path {
    my ($csi, $title, $header, $category) = @_;
    my $slug;

    if ($category eq 'campus-wide') {
        $slug = make_slug($header);
        return "$OUTDIR/campus-wide/$slug.md";
    }

    if ($category eq 'supplemental') {
        $slug = make_slug($header);
        return "$OUTDIR/supplemental/$slug.md";
    }

    if ($category eq 'detail-drawing') {
        $slug = make_slug($header);
        return "$OUTDIR/supplemental/detail-drawings/$slug.md";
    }

    if ($csi) {
        my ($div) = $csi =~ /^(\d{2})/;
        my $csi_slug = $csi;
        $csi_slug =~ s/\s+/-/g;
        my $title_slug = make_slug($title || '');
        $title_slug =~ s/^-//;
        # Remove date suffixes already stripped
        $title_slug =~ s/-+$//;
        return "$OUTDIR/division-$div/$csi_slug-$title_slug.md";
    }

    # Fallback
    $slug = make_slug($header);
    return "$OUTDIR/supplemental/$slug.md";
}

# ============================================================================
sub make_slug {
    my ($text) = @_;
    $text = lc($text);
    $text =~ s/_/-/g;
    $text =~ s/[^a-z0-9\-]+/-/g;
    $text =~ s/-{2,}/-/g;
    $text =~ s/^-|-$//g;
    # Truncate to reasonable length
    $text = substr($text, 0, 80) if length($text) > 80;
    $text =~ s/-$//;
    return $text;
}

# ============================================================================
sub resolve_duplicates {
    for my $csi (sort keys %csi_versions) {
        my @versions = @{$csi_versions{$csi}};
        next if @versions <= 1;

        # Sort by date (newest first); undated sorts last
        @versions = sort {
            my $da = parse_date_for_sort($a->{date});
            my $db = parse_date_for_sort($b->{date});
            $db cmp $da;
        } @versions;

        # Special case: different titles = different documents, keep both
        my %titles;
        for my $v (@versions) {
            my $clean = lc($v->{title});
            $clean =~ s/_\d{8}$//;
            $clean =~ s/\s+/ /g;
            $titles{$clean}++;
        }
        if (scalar(keys %titles) > 1) {
            print "  KEEP BOTH: CSI $csi has different documents: " . join(', ', keys %titles) . "\n";
            next;
        }

        # Winner is first (newest), rest go to archive
        my $winner = shift @versions;
        print "  WINNER: CSI $csi -> $winner->{path} (date: " . ($winner->{date}||'none') . ")\n";

        my $archive_dir = "$OUTDIR/archive";
        make_path($archive_dir) unless -d $archive_dir;

        for my $loser (@versions) {
            my $base = basename($loser->{path});
            # Add date to archive name if not already there
            if ($loser->{date} && $base !~ /\d{4}/) {
                my $d = $loser->{date};
                $d =~ s/[^0-9]/-/g;
                $base =~ s/\.md$/-$d.md/;
            } else {
                $base =~ s/\.md$/-old.md/;
            }
            my $archive_path = "$archive_dir/$base";
            print "  ARCHIVE: $loser->{path} -> $archive_path\n";
            rename $loser->{path}, $archive_path or warn "Cannot move $loser->{path}: $!\n";

            # Update manifest
            for my $m (@manifest) {
                if ($m->{path} eq $loser->{path}) {
                    $m->{path} = $archive_path;
                    $m->{category} = 'archived';
                }
            }
        }
    }
}

# ============================================================================
sub parse_date_for_sort {
    my ($d) = @_;
    return '0000-00-00' unless $d;

    # Already YYYY-MM-DD
    return $d if $d =~ /^\d{4}-\d{2}-\d{2}$/;

    # M-DD-YY or MM-DD-YY
    if ($d =~ /^(\d{1,2})-(\d{1,2})-(\d{2,4})$/) {
        my ($m, $day, $y) = ($1, $2, $3);
        $y = "20$y" if length($y) == 2 && $y < 50;
        $y = "19$y" if length($y) == 2 && $y >= 50;
        return sprintf("%04d-%02d-%02d", $y, $m, $day);
    }

    return $d;
}

# ============================================================================
sub split_oversized {
    for my $m (@manifest) {
        next if $m->{category} eq 'archived';
        next unless -f $m->{path};

        # Count actual lines
        open my $fh, '<:raw', $m->{path} or next;
        my @lines = <$fh>;
        close $fh;

        next if scalar(@lines) <= $MAX_LINES;

        print "  SPLIT: $m->{path} (" . scalar(@lines) . " lines)\n";

        # Find split points: PART N, Chapter N, or major numbered headings
        my @split_at;
        for my $i (0..$#lines) {
            if ($lines[$i] =~ /^(?:PART \d|Chapter \d|\d+\.\d+\s+[A-Z])/i && $i > 50) {
                push @split_at, $i;
            }
        }

        # If no structural boundaries, split at line count
        if (!@split_at) {
            my $chunk_size = int(scalar(@lines) / (int(scalar(@lines) / $MAX_LINES) + 1));
            for (my $i = $chunk_size; $i < scalar(@lines); $i += $chunk_size) {
                # Find nearest blank line
                my $best = $i;
                for my $j (($i-20)..($i+20)) {
                    if ($j >= 0 && $j < scalar(@lines) && $lines[$j] =~ /^\s*$/) {
                        $best = $j;
                        last;
                    }
                }
                push @split_at, $best;
            }
        }

        # Ensure we actually split into chunks <= MAX_LINES
        # Filter split points to keep only those that create proper-sized chunks
        my @good_splits;
        my $last_split = 0;
        for my $sp (sort { $a <=> $b } @split_at) {
            if ($sp - $last_split >= 200) {  # minimum chunk size
                push @good_splits, $sp;
                $last_split = $sp;
            }
        }

        next unless @good_splits;

        # Read the header (first ~8 lines)
        my $header_end = 0;
        for my $i (0..min(15, $#lines)) {
            if ($lines[$i] =~ /^---\s*$/) {
                $header_end = $i + 1;
                last;
            }
        }
        my @header_lines = @lines[0..$header_end];

        # Create chunks
        my @chunks;
        my $start = 0;
        for my $sp (@good_splits) {
            push @chunks, [@lines[$start..($sp-1)]];
            $start = $sp;
        }
        push @chunks, [@lines[$start..$#lines]];

        # Check if any chunk is still too large, and if so do a simple even split
        my $max_chunk = 0;
        for my $c (@chunks) { $max_chunk = scalar(@$c) if scalar(@$c) > $max_chunk; }
        if ($max_chunk > $MAX_LINES * 1.2) {
            # Fall back to even splitting
            my $n_parts = int(scalar(@lines) / ($MAX_LINES - 50)) + 1;
            my $chunk_size = int(scalar(@lines) / $n_parts);
            @chunks = ();
            for (my $i = 0; $i < scalar(@lines); $i += $chunk_size) {
                my $end = min($i + $chunk_size - 1, $#lines);
                push @chunks, [@lines[$i..$end]];
            }
        }

        # Write part files
        my $base = $m->{path};
        $base =~ s/\.md$//;
        unlink $m->{path};  # remove original

        my $total_parts = scalar(@chunks);
        for my $i (0..$#chunks) {
            my $part_num = $i + 1;
            my $part_path = "${base}-part${part_num}.md";

            open my $out, '>:raw', $part_path or die "Cannot write $part_path: $!\n";

            # Adjust header for part info
            if ($i == 0) {
                # First part keeps original header, add part info
                for my $hl (@{$chunks[$i]}) {
                    if ($hl =~ /^# /) {
                        $hl =~ s/\n$//;
                        print $out "$hl (Part $part_num of $total_parts)\n";
                    } else {
                        print $out $hl;
                    }
                }
            } else {
                # Subsequent parts get a minimal header
                my $title_line = $header_lines[0] || "# (continued)";
                $title_line =~ s/\n$//;
                $title_line =~ s/\)?\s*$//;
                $title_line =~ s/\(Part \d+ of \d+//;
                print $out "$title_line (Part $part_num of $total_parts)\n\n";
                print $out "> **Continued from:** " . basename("${base}-part" . ($part_num-1) . ".md") . "\n\n";
                print $out "---\n\n";
                for my $cl (@{$chunks[$i]}) {
                    print $out $cl;
                }
            }
            close $out;

            # Count lines
            open my $cnt, '<', $part_path or next;
            my $lc = 0; $lc++ while <$cnt>; close $cnt;

            push @manifest, {
                csi      => $m->{csi},
                title    => $m->{title} . " (Part $part_num of $total_parts)",
                date     => $m->{date},
                path     => $part_path,
                lines    => $lc,
                category => $m->{category},
            };

            print "    Part $part_num: $part_path ($lc lines)\n";
        }

        # Mark original manifest entry as split
        $m->{category} = 'split-removed';
    }
}

sub min { return $_[0] < $_[1] ? $_[0] : $_[1]; }

# ============================================================================
sub write_manifest {
    my $mpath = "$OUTDIR/MANIFEST.txt";
    open my $out, '>:raw', $mpath or die "Cannot write $mpath: $!\n";

    print $out "# WSU Design Standards - File Manifest\n";
    print $out "# Generated: " . localtime() . "\n\n";

    my $total_files = 0;
    my $total_lines = 0;

    for my $m (sort { $a->{path} cmp $b->{path} } @manifest) {
        next if $m->{category} eq 'split-removed';
        printf $out "%-12s | %-60s | %5d lines | %s | %s\n",
            $m->{csi} || '-',
            $m->{path},
            $m->{lines},
            $m->{category},
            $m->{date} || '-';
        $total_files++;
        $total_lines += $m->{lines};
    }

    print $out "\n# Total: $total_files files, $total_lines lines\n";
    close $out;
    print "\nManifest: $total_files files, $total_lines lines\n";
}
