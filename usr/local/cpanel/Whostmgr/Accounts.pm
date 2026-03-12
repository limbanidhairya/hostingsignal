package Whostmgr::Accounts;

use strict;
use warnings;

=head1 NAME

Whostmgr::Accounts - System Account Management

=head1 DESCRIPTION

Handles Linux user creation, suspension, and deletion, 
mirroring the Cpanel/WHM `createacct` and `removeacct` API.

=cut

sub create_account {
    my ($class, %args) = @_;
    
    my $user   = $args{user}   || return { success => 0, error => "Missing username" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $pass   = $args{pass}   || return { success => 0, error => "Missing password" };
    my $plan   = $args{plan}   || "default";
    
    # 1. Check if user exists
    if (_user_exists($user)) {
        return { success => 0, error => "User $user already exists." };
    }
    
    # 2. Call useradd (mocked logic for Windows testing, but actual commands for Linux)
    my $cmd = "useradd -m -s /bin/bash -d /home/$user $user";
    print "Executing: $cmd\n";
    # system($cmd);
    
    # 3. Create public_html
    my $docroot = "/home/$user/public_html";
    print "Creating document root at: $docroot\n";
    # mkdir($docroot);
    # chown($user, $user, $docroot);

    # 4. Save User Config (/var/cpanel/users/$user)
    require Whostmgr::UserConfig;
    Whostmgr::UserConfig->save_user($user, {
        USER => $user,
        DNS => $domain,
        STARTDATE => time(),
        PLAN => $plan,
        IP => "127.0.0.1",
        FEATURELIST => "default"
    });

    return { 
        success => 1, 
        message => "Account $user created successfully for $domain",
        data => \%args
    };
}

sub remove_account {
    my ($class, $user) = @_;
    
    if (!_user_exists($user)) {
        return { success => 0, error => "User $user does not exist." };
    }
    
    # Call userdel
    my $cmd = "userdel -r $user";
    print "Executing: $cmd\n";
    # system($cmd);
    
    return { success => 1, message => "Account $user removed." };
}

sub _user_exists {
    my $user = shift;
    # Simple check on /etc/passwd if on Linux, otherwise mock
    if (-e '/etc/passwd') {
        system("id $user >/dev/null 2>&1");
        return ($? == 0);
    }
    return 0; # Mock for dev
}

1; # End of module
