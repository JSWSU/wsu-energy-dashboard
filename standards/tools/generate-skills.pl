#!/usr/bin/perl
# generate-skills.pl — Create Claude Code skills for each CSI MasterFormat division.
# Usage: perl generate-skills.pl <standards-dir> <skills-dir>
#
# Creates one SKILL.md per division (00-40) plus a master orchestrator skill.

use strict;
use warnings;
use File::Path qw(make_path);
use File::Find;

my $STD_DIR  = shift || 'standards/wsu';
my $SKILL_DIR = shift || ($ENV{USERPROFILE} || $ENV{HOME}) . '/.claude/skills';

# CSI MasterFormat division names
my %DIV_NAMES = (
    '00' => 'Procurement and Contracting',
    '01' => 'General Requirements',
    '02' => 'Existing Conditions',
    '03' => 'Concrete',
    '04' => 'Masonry',
    '05' => 'Metals',
    '06' => 'Wood, Plastics, and Composites',
    '07' => 'Thermal and Moisture Protection',
    '08' => 'Openings',
    '09' => 'Finishes',
    '10' => 'Specialties',
    '11' => 'Equipment',
    '12' => 'Furnishings',
    '13' => 'Special Construction',
    '14' => 'Conveying Equipment',
    '15' => 'Reserved (Mechanical)',
    '16' => 'Reserved (Electrical)',
    '17' => 'Reserved',
    '18' => 'Reserved',
    '19' => 'Reserved',
    '20' => 'Reserved',
    '21' => 'Fire Suppression',
    '22' => 'Plumbing',
    '23' => 'HVAC',
    '24' => 'Reserved',
    '25' => 'Integrated Automation',
    '26' => 'Electrical',
    '27' => 'Communications',
    '28' => 'Electronic Safety and Security',
    '29' => 'Reserved',
    '30' => 'Reserved',
    '31' => 'Earthwork',
    '32' => 'Exterior Improvements',
    '33' => 'Utilities',
    '34' => 'Transportation',
    '35' => 'Waterway and Marine',
    '36' => 'Reserved',
    '37' => 'Reserved',
    '38' => 'Reserved',
    '39' => 'Reserved',
    '40' => 'Process Integration',
);

# Scan for files per division
my %div_files;
for my $d (0..40) {
    my $dd = sprintf("%02d", $d);
    my $dir = "$STD_DIR/division-$dd";
    next unless -d $dir;
    my @files;
    opendir my $dh, $dir or next;
    while (my $f = readdir $dh) {
        next unless $f =~ /\.md$/;
        my $path = "$dir/$f";
        open my $fh, '<', $path or next;
        my $lines = 0; $lines++ while <$fh>; close $fh;
        push @files, { name => $f, path => $path, lines => $lines };
    }
    closedir $dh;
    @files = sort { $a->{name} cmp $b->{name} } @files;
    $div_files{$dd} = \@files if @files;
}

# Also scan supplemental and campus-wide for relevant division prefixes
my %supp_files;
for my $subdir ('supplemental', 'supplemental/detail-drawings', 'campus-wide') {
    my $dir = "$STD_DIR/$subdir";
    next unless -d $dir;
    opendir my $dh, $dir or next;
    while (my $f = readdir $dh) {
        next unless $f =~ /\.md$/;
        my $path = "$dir/$f";
        # Try to extract division number from filename
        if ($f =~ /^(\d{2})-/) {
            push @{$supp_files{$1}}, { name => $f, path => $path, subdir => $subdir };
        }
    }
    closedir $dh;
}

# Generate per-division skills
for my $dd (sort keys %DIV_NAMES) {
    my $name = $DIV_NAMES{$dd};
    my $slug = lc($name);
    $slug =~ s/[^a-z0-9]+/-/g;
    $slug =~ s/^-|-$//g;
    $slug = substr($slug, 0, 40);
    $slug =~ s/-$//;

    my $skill_name = "wsu-div-$dd-$slug";
    my $skill_dir = "$SKILL_DIR/$skill_name";
    make_path($skill_dir) unless -d $skill_dir;

    my $has_content = exists $div_files{$dd};
    my $has_supp = exists $supp_files{$dd};

    open my $out, '>', "$skill_dir/SKILL.md" or die "Cannot write $skill_dir/SKILL.md: $!\n";

    # Frontmatter
    print $out "---\n";
    print $out "name: $skill_name\n";
    print $out "description: \"WSU Design Standard Division $dd - $name. ";
    if ($has_content) {
        my $count = scalar @{$div_files{$dd}};
        print $out "Use when reviewing Division $dd requirements. $count standard section(s) available.";
    } else {
        print $out "No WSU-specific standard exists for this division. Defer to applicable building codes.";
    }
    print $out "\"\n";
    print $out "---\n\n";

    # Header
    print $out "# WSU Design Standard: Division $dd - $name\n\n";

    if (!$has_content && !$has_supp) {
        print $out "> **Status:** No WSU-specific design standard exists for Division $dd.\n";
        print $out "> Defer to applicable building codes (NEC, IMC, IPC, NFPA, etc.) for this division.\n\n";
        print $out "## When This Division Applies\n\n";
        print $out "If a project includes work in Division $dd ($name), check:\n";
        print $out "1. Applicable building codes and standards\n";
        print $out "2. WSU campus-wide design guidelines (`standards/wsu/campus-wide/`)\n";
        print $out "3. Project-specific requirements in the contract documents\n";
        close $out;
        print "  Created: $skill_name (no WSU content)\n";
        next;
    }

    # Has content
    print $out "## Standard Files\n\n";
    print $out "Read these files from the knowledge base for Division $dd requirements:\n\n";
    print $out "| File | Lines | Description |\n";
    print $out "|------|------:|-------------|\n";

    if ($has_content) {
        for my $f (@{$div_files{$dd}}) {
            my $desc = $f->{name};
            $desc =~ s/\.md$//;
            $desc =~ s/^\d{2}-\d{2}-\d{2}(-\d{2})?-//;
            $desc =~ s/-/ /g;
            $desc = ucfirst($desc);
            print $out "| `standards/wsu/division-$dd/$f->{name}` | $f->{lines} | $desc |\n";
        }
    }

    if ($has_supp) {
        for my $f (sort { $a->{name} cmp $b->{name} } @{$supp_files{$dd}}) {
            print $out "| `standards/wsu/$f->{subdir}/$f->{name}` | - | Supplemental: $f->{name} |\n";
        }
    }

    print $out "\n## Review Checklist\n\n";
    print $out "When reviewing contractor drawings against Division $dd:\n\n";
    print $out "1. Read each standard file listed above\n";
    print $out "2. For each requirement in the standard, check if the contractor's design addresses it\n";
    print $out "3. Mark findings as: `[C]` Compliant, `[D]` Deviation, `[O]` Omission, `[X]` Concern\n";
    print $out "4. Record findings in `findings.md` with the CSI code, requirement, drawing reference, and standard citation\n";
    print $out "5. Note any items requiring formal WSU variance approval\n";

    close $out;
    my $tag = $has_content ? scalar(@{$div_files{$dd}}) . " files" : "supplemental only";
    print "  Created: $skill_name ($tag)\n";
}

# Generate master orchestrator skill
my $master_dir = "$SKILL_DIR/wsu-compliance-review";
make_path($master_dir) unless -d $master_dir;
open my $out, '>', "$master_dir/SKILL.md" or die "Cannot write master skill: $!\n";

print $out <<'MASTER';
---
name: wsu-compliance-review
description: "Master orchestrator for WSU design standards compliance reviews. Use when starting a new project review, generating compliance reports, or coordinating multi-discipline reviews against WSU Facilities Services standards."
---

# WSU Compliance Review — Master Orchestrator

## Overview

This skill orchestrates a full compliance review of contractor design drawings against WSU Facilities Services Design and Construction Standards.

## Workflow

### 1. Project Setup
- Read `standards/INDEX.md` to understand available standards
- Read or create `standards/projects/{project-name}/PROJECT-INFO.md`
- Determine applicable CSI divisions from the project scope

### 2. Division Reviews
For each applicable division, invoke the corresponding skill:
- `wsu-div-XX-{name}` — reads the standard files and guides the review

Dispatch reviews in parallel using subagents when possible:
- Group by discipline: Architectural (02-14), Fire (21, 28), Plumbing (22), HVAC (23, 25), Electrical (26-27), Civil (31-33, 40)

### 3. Findings Aggregation
- Collect all findings from division reviews into `findings.md`
- Assign finding numbers (F-001, F-002, ...) and severity (Critical/Major/Minor)
- Identify items requiring formal WSU variance approval
- Build the summary counts table (Compliant/Deviation/Omission/Concern per discipline)

### 4. Report Generation
Generate two synchronized reports:

**Word Report** (`report-word.md`):
- Copy `standards/REPORT-TEMPLATE-WORD.md` to the project folder
- Fill in all sections from findings data
- Include detailed descriptions with standard citations

**PPT Report** (`report-ppt.md`):
- Copy `standards/REPORT-TEMPLATE-PPT.md` to the project folder
- Fill in 16-slide structure from findings data
- Ensure every PPT finding appears in the Word report and vice versa

### 5. Quality Check
- Verify all findings have: CSI code, requirement, drawing reference, standard citation, severity
- Verify Word and PPT content are synchronized
- Verify summary counts match detailed findings
- List any gaps or sections not yet reviewed

## Status Notation
- `[C]` = Compliant — requirement is addressed in the design
- `[D]` = Deviation — design differs from WSU standard
- `[O]` = Omission — requirement is not addressed at all
- `[X]` = Concern — potential issue, needs clarification or further review
- `[ ]` = Not yet reviewed

## Severity Levels
- **Critical** — Code violation or life-safety issue
- **Major** — WSU standard violation that must be corrected
- **Minor** — Recommendation or preference, not a hard requirement

## Discipline Groupings (for PPT slides)
1. **Architectural / Finishes** — Divisions 02-14
2. **HVAC / Controls** — Divisions 23, 25
3. **Electrical** — Divisions 26, 27
4. **Plumbing** — Division 22
5. **Fire Protection** — Divisions 21, 28
6. **Civil / Site** — Divisions 31, 32, 33, 40
MASTER

close $out;
print "  Created: wsu-compliance-review (master orchestrator)\n";

print "\nDone. Skills written to $SKILL_DIR/\n";
