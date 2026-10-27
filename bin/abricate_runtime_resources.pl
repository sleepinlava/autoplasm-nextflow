#!/usr/bin/env perl
use strict;
use warnings;
use Cwd qw(abs_path);
use File::Basename qw(dirname basename);
use File::Spec;
use Digest::SHA;
use JSON::PP;
use MIME::Base64 qw(decode_base64);
use Getopt::Long;
use IPC::Open3;
use Symbol qw(gensym);

my $json = JSON::PP->new->canonical->ascii;
sub bytes {
    my ($path) = @_;
    open my $f, '<:raw', $path or die "Cannot read resource $path: $!\n";
    local $/; return <$f>;
}
sub resource {
    my ($root) = @_;
    my @entries;
    my $visit;
    $visit = sub {
        my ($p, $relative, $ancestors) = @_;
        my $link = -l $p ? readlink($p) : undef;
        my @before = stat($p); @before or die "Missing resource $p: $!\n";
        my $mode = $before[2] & 07777;
        if (-d _) {
            my $key = "$before[0]:$before[1]";
            die "Resource directory symlink cycle: $p\n" if $ancestors->{$key};
            push @entries, {path=>$relative,kind=>'directory',mode=>$mode,link=>$link};
            opendir my $d, $p or die "Cannot read directory $p: $!\n";
            my @names = sort grep { $_ ne '.' && $_ ne '..' } readdir($d); closedir $d;
            $visit->("$p/$_", "$relative/$_", {%$ancestors,$key=>1}) for @names;
        } elsif (-f _) {
            open my $f, '<:raw', $p or die "Cannot hash $p: $!\n";
            my $sha = Digest::SHA->new(256)->addfile($f)->hexdigest; close $f;
            my @after = stat($p);
            die "Resource changed while hashing: $p\n" unless @after &&
                join(':',@before[0,1,2,7,9]) eq join(':',@after[0,1,2,7,9]);
            push @entries, {path=>$relative,kind=>'file',mode=>$mode,link=>$link,bytes=>$after[7],sha256=>$sha};
        } else { die "Resource member is not regular file/directory: $p\n"; }
    };
    $visit->($root,'.',{}); return \@entries;
}
sub executable {
    my ($name) = @_;
    for my $d (File::Spec->path) {
        my $p = File::Spec->catfile($d,$name);
        return File::Spec->rel2abs($p) if -f $p && -x $p;
    }
    die "Required ABRicate executable not found: $name\n";
}
sub command {
    my (@cmd) = @_;
    my $err = gensym;
    my $pid = open3(undef,my $out,$err,@cmd);
    local $/; my $stdout=<$out> // ''; my $stderr=<$err> // '';
    waitpid($pid,0);
    die "Resource command failed (@cmd): $stderr\n" if $?;
    return $stdout;
}
sub native_options {
    my ($entry,@args) = @_;
    # Evaluate the trusted installed release in a separate Perl process.
    # Only insert a return point immediately after its original Getopt::Long
    # parser/default assignment; no dependency or scientific command executes.
    my $driver = <<'DRIVER';
use strict; use JSON::PP;
$0 = shift @ARGV;
require FindBin; FindBin::again();
open my $f, '<', $0 or die $!; my $source=do {local $/; <$f>};
$source =~ /my \$VERSION = "1\.0\.1";/ or die "Requires ABRicate1.0.1\n";
my $replacement=q{setOptions(); print JSON::PP->new->canonical->ascii->encode({version=>$VERSION,datadir=>$datadir,db=>$db,minid=>$minid,mincov=>$mincov,threads=>$threads,noheader=>$noheader,csv=>$csv,nopath=>$nopath,fofn=>$fofn,summary=>$summary,list=>$list,setupdb=>$setupdb,check=>$check,files=>\@ARGV}); exit;};
my $count=($source =~ s/\bsetOptions\(\);/$replacement/);
$count==1 or die "Cannot identify native option-parser boundary\n";
eval $source; die $@ if $@;
DRIVER
    return $json->decode(command($^X,'-e',$driver,$entry,@args));
}
sub prefix_members {
    my ($prefix) = @_;
    my $dir = dirname($prefix); my $name = basename($prefix);
    opendir my $d,$dir or die "Missing BLAST volume directory $dir: $!\n";
    my @names = sort grep { $_ eq $name || index($_,"$name.")==0 } readdir($d); closedir $d;
    @names or die "Missing BLAST prefix members: $prefix\n";
    return {map { $_ => resource("$dir/$_") } @names};
}
sub capture {
    my ($runtime,@args) = @_;
    my $entry = executable('abricate');
    my $parsed = native_options($entry,@args);
    die "Prepare ABRicate databases with --setupdb before resource lookup\n" if $parsed->{setupdb};
    my %tools = map { $_ => executable($_) } qw(blastn blastx makeblastdb blastdbcmd any2fasta gzip unzip bash);
    my %resources = (entrypoint=>resource($entry),perl=>resource($^X),resolver=>resource($0),
                     executables=>{map { $_=>resource($tools{$_}) } sort keys %tools});
    my %locations = (entrypoint=>$entry,perl=>$^X,executables=>\%tools);
    # Respect native --fofn precedence and Path::Tiny's exact line reader.
    my @files = @{$parsed->{files}};
    if ($parsed->{fofn}) {
        require Path::Tiny;
        $resources{fofn}=resource($parsed->{fofn});
        @files=Path::Tiny::path($parsed->{fofn})->lines({chomp=>1});
    }
    $resources{inputs} = [map {resource($_)} @files];
    if (!$parsed->{summary} && !$parsed->{check}) {
        my $datadir = abs_path($parsed->{datadir}) or die "Missing ABRicate datadir\n";
        $locations{datadir}=$datadir;
        if ($parsed->{list}) { $resources{database_directory}=resource($datadir); }
        else {
            my $selected = "$datadir/$parsed->{db}";
            $resources{selected_database_directory}=resource($selected);
            my $prefix="$selected/sequences";
            my $info=command($tools{blastdbcmd},'-info','-db',$prefix);
            my @volumes = $info =~ /^\s*Volumes:\s*\n([\s\S]*)/m ? split(/\n/,$1) : ();
            @volumes=grep {length} map {s/^\s+|\s+$//gr} @volumes;
            @volumes or die "Cannot identify BLAST database volume read set: $prefix\n";
            $resources{blast_volumes}={map { $_=>prefix_members($_) } @volumes};
            $locations{selected_prefix}=$prefix;
            $locations{blast_volumes}=\@volumes;
        }
    }
    # Threads are in the consumer command/cache key. The probe can hash with
    # its own CPU quota without differing solely because of that allocation.
    delete $parsed->{threads};
    return {schema_version=>1,tool=>'ABRicate',version=>$parsed->{version},execution_adapter=>'1.0.1_pipefail_close_v1',runtime=>$runtime,
            parsed_arguments=>$parsed,resources=>\%resources,resolved_locations=>\%locations};
}
my ($runtime64,$output,$verify,$execute);
Getopt::Long::Configure('require_order','no_auto_abbrev');
GetOptions('runtime-base64=s'=>\$runtime64,'output=s'=>\$output,'verify=s'=>\$verify,'execute!'=>\$execute) or die "Invalid resolver options\n";
$runtime64 or die "--runtime-base64 required\n";
my $identity=capture($json->decode(decode_base64($runtime64)),@ARGV);
my $encoded=$json->encode($identity);
die "ABRicate runtime resources or resolved arguments differ from pre-lookup identity\n" if defined($verify) && $json->encode($json->decode(bytes($verify))) ne $encoded;
if (defined $output) {open my $f,'>:raw',$output or die $!; print $f "$encoded\n"; close $f;}
if ($execute) {
    defined($verify) or die "--execute requires verified pre-lookup receipt\n";
    # Fixed upstream1.0.1 neither enables pipeline failure propagation nor
    # checks close(BLAST). Preserve its program/argv/thresholds, with exactly
    # these two error-boundary checks in the trusted source evaluation.
    my $driver = <<'DRIVER';
use strict;
$0=shift @ARGV;
require FindBin; FindBin::again();
open my $f,'<',$0 or die $!; my $source=do {local $/; <$f>};
$source =~ /my \$VERSION = "1\.0\.1";/ or die "Requires ABRicate1.0.1\n";
my $open_code=q{open BLAST, '-|', 'bash', '-o', 'pipefail', '-c', $cmd or err("Cannot start ABRicate search pipeline");};
my $open=($source =~ s{open BLAST, "\$cmd \|";}{$open_code});
my $close_code=q{close BLAST or err("ABRicate input converter/BLAST subprocess failed (status $?)");};
my $close=($source =~ s{close BLAST;}{$close_code});
$open==1 && $close==1 or die "Cannot identify fixed ABRicate subprocess boundaries\n";
eval $source; die $@ if $@;
DRIVER
    exec {$^X} $^X,'-e',$driver,$identity->{resolved_locations}{entrypoint},@ARGV;
    die "Cannot execute ABRicate: $!\n";
}
