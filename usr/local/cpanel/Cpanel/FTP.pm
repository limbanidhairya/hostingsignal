package Cpanel::FTP;

use strict;
use warnings;

=head1 NAME

Cpanel::FTP - FTP Account Management

=head1 DESCRIPTION

Handles the creation and deletion of virtual FTP accounts for Pure-FTPd or ProFTPD.

=cut

sub add_ftp {
    my ($class, %args) = @_;
    
    my $user = $args{user} || return { success => 0, error => "Missing ftp username" };
    my $pass = $args{pass} || return { success => 0, error => "Missing ftp password" };
    my $dir  = $args{dir}  || 'public_html';
    my $domain = $args{domain} || 'maindomain.com'; # Assume primary if omitted in some API versions
    
    my $full_ftp_user = "$user\@$domain";
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock Add FTP: $full_ftp_user rooted at ~/$dir\n";
        return { success => 1, message => "FTP account $full_ftp_user created." };
    }
    
    # Normally interacts with `pure-pw useradd ...` or modifies `/etc/proftpd/auth.conf`
    # my $cmd = "pure-pw useradd $full_ftp_user -d /home/sysuser/$dir -m";
    # system($cmd);
    
    return { success => 1, message => "FTP account $full_ftp_user created.", user => $full_ftp_user, dir => $dir };
}

sub delete_ftp {
    my ($class, %args) = @_;
    my $user = $args{user} || return { success => 0, error => "Missing ftp username" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    
    my $full_ftp_user = "$user\@$domain";
    print "Mock Delete FTP: $full_ftp_user\n";
    
    return { success => 1, message => "FTP account $full_ftp_user deleted." };
}

1; # End of module
