#!/usr/bin/perl
# Minimal static file server for local dashboard development.
# Usage: perl serve.pl [port]   (default 8080)
use strict;
use warnings;
use IO::Socket::INET;
use File::Basename;
use Cwd 'abs_path';

my $port = $ARGV[0] || 8080;
my $root = dirname(abs_path($0));

my %mime = (
    html => 'text/html',       css  => 'text/css',
    js   => 'application/javascript', json => 'application/json',
    png  => 'image/png',       jpg  => 'image/jpeg',
    gif  => 'image/gif',       svg  => 'image/svg+xml',
    ico  => 'image/x-icon',    txt  => 'text/plain',
    bas  => 'text/plain',
);

my $srv = IO::Socket::INET->new(
    LocalAddr => '127.0.0.1', LocalPort => $port,
    Proto => 'tcp', Listen => 5, ReuseAddr => 1,
) or die "Cannot bind to port $port: $!\n";

print "Serving $root on http://localhost:$port\n";

while (my $c = $srv->accept) {
    my $req = <$c>;
    next unless $req && $req =~ m{^GET\s+(/\S*)\s+HTTP};
    my $path = $1;
    $path =~ s/\?.*//;              # strip query string
    $path = '/index.html' if $path eq '/';
    $path =~ s{/\.\.}{}g;           # basic directory traversal guard

    my $file = "$root$path";
    $file =~ s{/}{\\}g if $^O eq 'MSWin32';

    if (-f $file) {
        open my $fh, '<:raw', $file or next;
        local $/; my $body = <$fh>; close $fh;
        my ($ext) = $file =~ /\.(\w+)$/;
        my $ct = $mime{lc($ext // '')} // 'application/octet-stream';
        print $c "HTTP/1.0 200 OK\r\nContent-Type: $ct\r\nContent-Length: " . length($body) . "\r\nAccess-Control-Allow-Origin: *\r\n\r\n$body";
    } else {
        my $msg = "404 Not Found: $path";
        print $c "HTTP/1.0 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: " . length($msg) . "\r\n\r\n$msg";
    }
    close $c;
}
