package HS::Auth;

use strict;
use warnings;
use JSON;
use Digest::SHA qw(sha256_hex);
use File::Path qw(make_path);

require HS::Account;

my $SESSION_DB = "/var/hspanel/userdata/sessions.json";
my $SESSION_TTL = 3600 * 12;

sub _load_sessions {
    return {} unless -f $SESSION_DB;
    open(my $fh, '<', $SESSION_DB) or return {};
    my $raw = do { local $/; <$fh> };
    close($fh);
    return {} unless $raw;
    my $data = eval { decode_json($raw) };
    return $data || {};
}

sub _save_sessions {
    my ($data) = @_;
    my $dir = $SESSION_DB;
    $dir =~ s|/[^/]+$||;
    make_path($dir) unless -d $dir;

    open(my $fh, '>', $SESSION_DB) or return 0;
    print $fh to_json($data, { pretty => 1 });
    close($fh);
    return 1;
}

sub login {
    my ($class, %args) = @_;
    my $username = $args{username} || '';
    my $password = $args{password} || '';

    my $auth = HS::Account->authenticate(username => $username, password => $password);
    return $auth unless $auth->{success};

    my $now = time;
    my $token = sha256_hex(join(':', $username, $now, rand(), $$));

    my $sessions = _load_sessions();
    $sessions->{$token} = {
        username   => $username,
        created_at => $now,
        expires_at => $now + $SESSION_TTL,
    };

    _save_sessions($sessions) or return { success => 0, error => "Failed to persist session" };

    return {
        success    => 1,
        token      => $token,
        username   => $username,
        expires_in => $SESSION_TTL,
    };
}

sub validate {
    my ($class, %args) = @_;
    my $token = $args{token} || return { success => 0, error => "Missing token" };

    my $sessions = _load_sessions();
    my $entry = $sessions->{$token};
    return { success => 0, error => "Session not found" } unless $entry;

    if (($entry->{expires_at} || 0) < time) {
        delete $sessions->{$token};
        _save_sessions($sessions);
        return { success => 0, error => "Session expired" };
    }

    return {
        success  => 1,
        username => $entry->{username},
        expires  => $entry->{expires_at},
    };
}

sub logout {
    my ($class, %args) = @_;
    my $token = $args{token} || return { success => 0, error => "Missing token" };

    my $sessions = _load_sessions();
    delete $sessions->{$token};
    _save_sessions($sessions);

    return { success => 1, message => "Logged out" };
}

sub cleanup_expired {
    my ($class, %args) = @_;
    my $sessions = _load_sessions();
    my $now = time;

    my $removed = 0;
    for my $token (keys %$sessions) {
        if (($sessions->{$token}{expires_at} || 0) < $now) {
            delete $sessions->{$token};
            $removed++;
        }
    }

    _save_sessions($sessions);
    return { success => 1, removed => $removed };
}

1;
