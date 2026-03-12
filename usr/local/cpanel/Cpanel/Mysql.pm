package Cpanel::Mysql;

use strict;
use warnings;
use DBI;

=head1 NAME

Cpanel::Mysql - Database Management

=head1 DESCRIPTION

Interfaces with MySQL/MariaDB to manage cPanel user databases.
Connects via local socket using root privileges.

=cut

sub create_database {
    my ($class, %args) = @_;
    
    my $db_name = $args{db} || return { success => 0, error => "Missing database name" };
    my $cp_user = $args{user} || return { success => 0, error => "Missing system user" };
    
    # Normally, cPanel requires $cp_user prefix on databases (e.g. username_db)
    my $full_db_name = "${cp_user}_${db_name}";
    
    # Mocking Database Connection
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock DB Create Executed: CREATE DATABASE $full_db_name\n";
        return { success => 1, message => "Database $full_db_name created." };
    }
    
    # Real logic implementation
    my $dbh;
    eval {
        $dbh = DBI->connect("DBI:mysql:database=mysql;host=localhost", "root", "", {
            PrintError => 0,
            RaiseError => 1, 
            AutoCommit => 1 
        });
        
        my $sth = $dbh->prepare("CREATE DATABASE `$full_db_name`");
        $sth->execute();
    };
    
    if ($@) {
        return { success => 0, error => "Database creation failed: $@" };
    }
    
    $dbh->disconnect() if $dbh;
    
    return { success => 1, message => "Database $full_db_name created." };
}

sub create_user {
    my ($class, %args) = @_;
    
    my $db_user = $args{dbuser} || return { success => 0, error => "Missing user name" };
    my $pass    = $args{password} || return { success => 0, error => "Missing password" };
    my $cp_user = $args{user} || return { success => 0, error => "Missing system user" };
    
    my $full_user_name = "${cp_user}_${db_user}";
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock User Create Executed: CREATE USER $full_user_name\n";
        return { success => 1, message => "User $full_user_name created." };
    }
    
    my $dbh;
    eval {
        $dbh = DBI->connect("DBI:mysql:database=mysql;host=localhost", "root", "", { RaiseError => 1, AutoCommit => 1 });
        my $sth = $dbh->prepare("CREATE USER ?\@'localhost' IDENTIFIED BY ?");
        $sth->execute($full_user_name, $pass);
    };
    
    if ($@) {
        return { success => 0, error => "User creation failed: $@" };
    }
    
    $dbh->disconnect() if $dbh;
    
    return { success => 1, message => "User $full_user_name created." };
}

sub set_privileges {
    my ($class, %args) = @_;
    
    my $db_name = $args{db} || return { success => 0, error => "Missing database name" };
    my $db_user = $args{dbuser} || return { success => 0, error => "Missing user name" };
    my $cp_user = $args{user} || return { success => 0, error => "Missing system user" };
    
    my $full_db_name = "${cp_user}_${db_name}";
    my $full_user_name = "${cp_user}_${db_user}";
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock Privileges Executed on $full_db_name for $full_user_name\n";
        return { success => 1, message => "Privileges updated." };
    }
    
    my $dbh;
    eval {
        $dbh = DBI->connect("DBI:mysql:database=mysql;host=localhost", "root", "", { RaiseError => 1, AutoCommit => 1 });
        my $sth = $dbh->prepare("GRANT ALL PRIVILEGES ON `$full_db_name`.* TO ?\@'localhost'");
        $sth->execute($full_user_name);
        $dbh->do("FLUSH PRIVILEGES");
    };
    
    if ($@) {
        return { success => 0, error => "Failed to set privileges: $@" };
    }
    
    $dbh->disconnect() if $dbh;
    return { success => 1, message => "Privileges granted." };
}

1; # End of module
