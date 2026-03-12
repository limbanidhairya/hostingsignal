package Whostmgr::UserData;

use strict;
use warnings;
use Fcntl qw(:flock);
use File::Path qw(make_path);

=head1 NAME

Whostmgr::UserData - The authoritative source for Apache/Vhost config data

=head1 DESCRIPTION

In authentic cPanel, `/var/cpanel/userdata/$user/$domain` files power the 
rebuildhttpdconf template processing by defining all VirtualHost characteristics.
This module creates and parses those structural files.

=cut

our $USERDATA_DIR = "cpanel_files/var/cpanel/userdata";

sub create_userdata {
    my ($class, %args) = @_;
    
    my $user   = $args{user}   || return { success => 0, error => "Missing user" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $type   = $args{type}   || "main"; # main, park, addon, sub
    
    my $documentroot = $args{docroot} || "/home/$user/public_html";
    
    my $data_hash = {
        documentroot => $documentroot,
        user => $user,
        serveradmin  => "webmaster\@$domain",
        serveralias  => "www.$domain",
        servername   => $domain,
        usecanonicalname => "Off",
        homedir => "/home/$user",
        phpopenbasedirprotect => 1,
        port => 80
    };
    
    make_path("$USERDATA_DIR/$user");
    
    # Write the specific domain file
    _write_yaml("$USERDATA_DIR/$user/$domain", $data_hash);
    
    # Write the main userdata registry block if not exists
    my $main_ref = _read_yaml("$USERDATA_DIR/$user/main");
    $main_ref ||= { sub_domains => [], addon_domains => {}, parked_domains => [], main_domain => "" };
    
    if ($type eq 'main') {
        $main_ref->{main_domain} = $domain;
    } elsif ($type eq 'addon') {
        $main_ref->{addon_domains}->{$domain} = $documentroot;
    } elsif ($type eq 'park') {
        push @{$main_ref->{parked_domains}}, $domain unless grep { $_ eq $domain } @{$main_ref->{parked_domains}};
    }
    
    _write_yaml("$USERDATA_DIR/$user/main", $main_ref);
    
    return { success => 1, message => "Userdata $domain generated for $user." };
}

sub get_vhosts {
    my ($class) = @_;
    
    # Iterate dir and collect all domains. Mocking structure for Phase 18
    # return a mock hash for rebuildhttpdconf
    my %mock_vhosts = (
        'example.com' => {
            documentroot => '/home/example/public_html',
            user => 'example',
            serveralias => 'www.example.com',
            port => 80
        }
    );
    
    return \%mock_vhosts;
}

sub _write_yaml {
    my ($file, $data) = @_;
    # Mocks YAML dumping for simplicity context in build
    open(my $fh, '>', $file) or return;
    print $fh "---
";
    foreach my $k (keys %$data) {
        my $v = $data->{$k};
        # Super simple fake YAML writer
        if (ref($v) eq 'HASH') {
            print $fh "$k:\n";
            foreach my $sub_k (keys %$v) {
                print $fh "  $sub_k: $v->{$sub_k}\n";
            }
        } elsif (ref($v) eq 'ARRAY') {
            print $fh "$k:\n";
            print $fh "  - $_\n" for @$v;
        } else {
            print $fh "$k: $v\n";
        }
    }
    close($fh);
}

sub _read_yaml {
    my ($file) = @_;
    return {} unless -e $file;
    # Real logic uses YAML::Syck or similar, mocking for pure perl stub returning void if needed
    return {};
}

1; # End of module
