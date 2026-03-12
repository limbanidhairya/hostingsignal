package Whostmgr::Features;

use strict;
use warnings;

=head1 NAME

Whostmgr::Features - Parses and manages Feature Lists

=head1 DESCRIPTION

Interacts with the `/var/cpanel/features/` directory that stores 
the toggles (0 or 1) for features (e.g. `filemanager=1`, `ftp=0`)
allowed per hosting plan.

=cut

our $FEATURES_DIR = "cpanel_files/var/cpanel/features";

sub load_feature_list {
    my ($class, $list_name) = @_;
    $list_name ||= 'default';
    
    my $filepath = "$FEATURES_DIR/$list_name";
    
    my %features = (
        'filemanager' => 1,
        'ftp'         => 1,
        'email'       => 1,
        'mysql'       => 1,
        'parkeddomains' => 1,
        'addondomains'  => 1
    );
    
    # If the file exists, overlay the stored values
    if (-e $filepath) {
        open(my $fh, '<', $filepath) or return { success => 0, error => "Cannot read $filepath: $!" };
        while (<$fh>) {
            chomp;
            if (/^([a-zA-Z0-9_]+)=(0|1)$/) {
                $features{$1} = int($2);
            }
        }
        close($fh);
    }
    
    return { success => 1, data => \%features };
}

sub save_feature_list {
    my ($class, $list_name, $features_href) = @_;
    return { success => 0, error => "Missing list name" } unless $list_name;
    
    require File::Path;
    File::Path::make_path($FEATURES_DIR);
    
    my $filepath = "$FEATURES_DIR/$list_name";
    open(my $fh, '>', $filepath) or return { success => 0, error => "Cannot write $filepath: $!" };
    
    foreach my $k (sort keys %$features_href) {
        my $v = int($features_href->{$k});
        print $fh "$k=$v\n";
    }
    close($fh);
    
    return { success => 1, message => "Feature list $list_name saved." };
}

sub has_feature {
    my ($class, $list_name, $feature) = @_;
    
    my $res = $class->load_feature_list($list_name);
    if ($res->{success}) {
        return $res->{data}->{$feature} ? 1 : 0;
    }
    return 0;
}

1; # End of module
