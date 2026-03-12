package Cpanel::Email;

use strict;
use warnings;
use JSON;
use File::Path qw(make_path);

=head1 NAME

Cpanel::Email - Email Account Management

=head1 DESCRIPTION

Handles the creation, quota management, and deletion of virtual email accounts
(POP3/IMAP), interacting with Exim/Postfix and Dovecot underlying structures.

=cut

sub add_pop {
    my ($class, %args) = @_;
    
    my $email = $args{email} || return { success => 0, error => "Missing email prefix" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $password = $args{password} || return { success => 0, error => "Missing password" };
    my $quota = $args{quota} || 250; # 250MB default
    
    my $full_email = "$email\@$domain";
    
    # In cPanel, virtual users are usually mapped in /etc/vmail or similar
    # e.g., /home/$cpanel_user/etc/$domain/passwd
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock Add POP: $full_email with quota ${quota}MB\n";
        return { success => 1, message => "Account $full_email created", email => $full_email };
    }
    
    # Hypothetical file write mimicking a standard Exim/Dovecot basic vhosts setup
    my $pwd_file = "cpanel_files/etc/$domain/passwd";
    make_path("cpanel_files/etc/$domain");
    
    open(my $fh, '>>', $pwd_file) or return { success => 0, error => "Cannot open auth file" };
    # Dovecot formatting: user:password:uid:gid::home::userdb_quota_rule=*:storage=250M
    # Passwords should be digested, using clear text just for syntax demonstration in this clone.
    print $fh "$email:{PLAIN}$password:1000:1000::/home/mock_user/mail/$domain/$email::userdb_quota_rule=*:storage=${quota}M\n";
    close($fh);
    
    return { success => 1, message => "Account $full_email created", email => $full_email };
}

sub delete_pop {
    my ($class, %args) = @_;
    
    my $email = $args{email} || return { success => 0, error => "Missing email" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $full_email = "$email\@$domain";
    
    print "Mock Delete POP: $full_email\n";
    
    return { success => 1, message => "Account $full_email deleted" };
}

1; # End of module
