package Cpanel::AppInstaller;

use strict;
use warnings;
use File::Path qw(make_path);

=head1 NAME

Cpanel::AppInstaller - Softaculous / WP Toolkit clone module

=head1 DESCRIPTION

Simulates the UAPI mechanisms for one-click installing applications
such as WordPress onto active cPanel domains.

=cut

sub install_wordpress {
    my ($class, %args) = @_;
    
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $user   = $args{user}   || return { success => 0, error => "Missing user" };
    my $title  = $args{title}  || "My WordPress Site";
    my $admin  = $args{admin}  || "admin";
    my $pass   = $args{adminpass} || return { success => 0, error => "Missing adminpass" };
    
    my $docroot = "/home/$user/public_html";
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock WP Install: Downloading WP to $docroot for $domain\n";
        print "Mock WP Install: Creating Database ${user}_wp...\n";
        
        require Cpanel::Mysql;
        Cpanel::Mysql->create_database(db => 'wp', user => $user);
        Cpanel::Mysql->create_user(dbuser => 'wpuser', password => $pass, user => $user);
        Cpanel::Mysql->set_privileges(db => 'wp', dbuser => 'wpuser', user => $user);
        
        # Mocking writing wp-config.php
        make_path("cpanel_files/home/$user/public_html");
        open(my $fh, '>', "cpanel_files/home/$user/public_html/wp-config.php");
        print $fh "<?php\n// Mock WP Config\ndefine('DB_NAME', '${user}_wp');\n";
        close($fh);
    }
    
    return { 
        success => 1, 
        message => "WordPress successfully installed on $domain" 
    };
}

sub list_installed {
    my ($class, $user) = @_;
    
    # Mock return list
    my @apps = (
        { app => 'WordPress', domain => 'example.com', version => '6.4.1', path => '/home/exampleuser/public_html' }
    );
    
    return { success => 1, data => \@apps };
}

1; # End of module
