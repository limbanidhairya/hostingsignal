package HS::Mail;

use strict;
use warnings;
use JSON;
use File::Path qw(make_path);

my $VMAIL_DIR  = "/var/hspanel/mail";
my $MAIL_DB    = "/var/hspanel/conf/mail_accounts.json";
my $POSTFIX_DIR = "/etc/postfix";
my $POSTFIX_MAILBOXES = "$POSTFIX_DIR/virtual_mailboxes";
my $POSTFIX_DOMAINS   = "$POSTFIX_DIR/virtual_domains";
my $DOVECOT_USERS     = "/etc/dovecot/users";
my $WRAP_SYSOP        = "/usr/local/hspanel/bin/wrap_sysop";

sub _run_first_success {
    my (@commands) = @_;
    for my $cmd (@commands) {
        my $rc = system(@$cmd);
        return 1 if $rc == 0;
    }
    return 0;
}

sub _reload_mail_services {
    _run_first_success(
        [$WRAP_SYSOP, 'reload_postfix'],
        ['/bin/systemctl', 'reload', 'postfix'],
        ['/bin/systemctl', 'restart', 'postfix'],
    );

    _run_first_success(
        [$WRAP_SYSOP, 'reload_dovecot'],
        ['/bin/systemctl', 'reload', 'dovecot'],
        ['/bin/systemctl', 'restart', 'dovecot'],
    );
}

sub _load_db {
    my $db = {};
    if (-f $MAIL_DB) {
        open(my $fh, '<', $MAIL_DB) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $MAIL_DB;
    $dir =~ s|/[^/]+$||;
    system("mkdir -p $dir") unless -d $dir;
    open(my $fh, '>', $MAIL_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub _hash_password {
    my ($password) = @_;
    my $cmd = "doveadm pw -s SHA512-CRYPT -p '$password' 2>/dev/null";
    my $hash = `$cmd`;
    chomp($hash);
    return $hash;
}

sub _write_mail_files {
    my ($db) = @_;

    make_path($POSTFIX_DIR) unless -d $POSTFIX_DIR;
    make_path('/etc/dovecot') unless -d '/etc/dovecot';

    my %domains;
    my @mailboxes;
    my @users;

    for my $email (sort keys %$db) {
        my $entry = $db->{$email};
        my ($user, $domain) = split(/\@/, $email, 2);
        next unless $user && $domain;
        $domains{$domain} = 1;

        my $maildir = "$VMAIL_DIR/$domain/$user";
        push @mailboxes, "$email\t$domain/$user/";

        my $hash = $entry->{password_hash} || '';
        push @users, "$email:$hash:5000:5000::$maildir::userdb_quota_rule=*:storage=" . ($entry->{quota_mb} || 500) . "M";
    }

    open(my $d, '>', $POSTFIX_DOMAINS) or return 0;
    print $d join("\n", sort keys %domains) . "\n";
    close($d);

    open(my $m, '>', $POSTFIX_MAILBOXES) or return 0;
    print $m join("\n", @mailboxes) . "\n" if @mailboxes;
    close($m);

    open(my $u, '>', $DOVECOT_USERS) or return 0;
    print $u join("\n", @users) . "\n" if @users;
    close($u);

    _run_first_success(
        ['/usr/sbin/postmap', $POSTFIX_DOMAINS],
        ['/sbin/postmap', $POSTFIX_DOMAINS],
        ['postmap', $POSTFIX_DOMAINS],
    );
    _run_first_success(
        ['/usr/sbin/postmap', $POSTFIX_MAILBOXES],
        ['/sbin/postmap', $POSTFIX_MAILBOXES],
        ['postmap', $POSTFIX_MAILBOXES],
    );

    _reload_mail_services();

    return 1;
}

sub list_accounts {
    my ($class, %args) = @_;
    my $domain = $args{domain};
    my $db = _load_db();

    my @accounts;
    for my $email (sort keys %$db) {
        next if $domain && $db->{$email}{domain} ne $domain;
        push @accounts, {
            email    => $email,
            domain   => $db->{$email}{domain},
            quota_mb => $db->{$email}{quota_mb} || 500,
            used_mb  => $db->{$email}{used_mb}  || 0,
            status   => $db->{$email}{status}   || 'active',
            created  => $db->{$email}{created}  || '2026-01-01',
        };
    }

    return { success => 1, accounts => \@accounts, total => scalar @accounts };
}

sub create {
    my ($class, %args) = @_;

    my $user   = $args{user}   || return { success => 0, error => "Missing user" };
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $password = $args{password} || return { success => 0, error => "Missing password" };
    my $quota  = $args{quota_mb} || 500;

    return { success => 0, error => "Invalid user format" }
        unless $user =~ /^[a-z0-9._-]{1,64}$/;

    my $email = "$user\@$domain";
    my $db = _load_db();

    return { success => 0, error => "Email account already exists" }
        if exists $db->{$email};

    my $hash = _hash_password($password);
    return { success => 0, error => "Failed to hash password" } unless $hash;

    $db->{$email} = {
        domain   => $domain,
        quota_mb => $quota,
        used_mb  => 0,
        password_hash => $hash,
        status   => 'active',
        created  => scalar localtime(),
    };

    _save_db($db);

    my $maildir = "$VMAIL_DIR/$domain/$user/Maildir";
    make_path($maildir) unless -d $maildir;

    return { success => 0, error => "Failed to update mail config files" }
        unless _write_mail_files($db);

    return {
        success => 1,
        message => "Email account $email created successfully.",
        email   => $email,
        quota_mb => $quota,
    };
}

sub delete {
    my ($class, %args) = @_;
    my $email = $args{email} || return { success => 0, error => "Missing email" };

    my $db = _load_db();
    return { success => 0, error => "Account not found" }
        unless exists $db->{$email};

    delete $db->{$email};
    _save_db($db);

    _write_mail_files($db);

    return { success => 1, message => "Email account $email deleted." };
}

sub change_password {
    my ($class, %args) = @_;
    my $email    = $args{email}    || return { success => 0, error => "Missing email" };
    my $password = $args{password} || return { success => 0, error => "Missing password" };

    my $db = _load_db();
    return { success => 0, error => "Account not found" }
        unless exists $db->{$email};

    my $hash = _hash_password($password);
    return { success => 0, error => "Failed to hash password" } unless $hash;

    $db->{$email}{password_hash} = $hash;
    _save_db($db);

    return { success => 0, error => "Failed to update mail config files" }
        unless _write_mail_files($db);

    return { success => 1, message => "Password changed for $email." };
}

sub get_quota {
    my ($class, %args) = @_;
    my $email = $args{email} || return { success => 0, error => "Missing email" };

    my $db = _load_db();
    return { success => 0, error => "Account not found" }
        unless exists $db->{$email};

    return {
        success  => 1,
        email    => $email,
        quota_mb => $db->{$email}{quota_mb} || 500,
        used_mb  => $db->{$email}{used_mb}  || 0,
    };
}

1;
