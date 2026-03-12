#!/usr/bin/perl
# cpsrvd - HostingSignal clone of cPanel's core service daemon
# Listens on 2082 (cPanel) and 2086 (WHM)

use strict;
use warnings;
use IO::Socket::INET;
use IO::Select;
use HTML::Template;
use JSON;

my $WHM_PORT = 2086;
my $CPANEL_PORT = 2082;
my $WEBMAIL_PORT = 2095;

print "Starting HostingSignal cpsrvd...\n";

# Bind WHM socket
my $whm_server = IO::Socket::INET->new(
    LocalPort => $WHM_PORT,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10
) or die "Couldn't bind WHM port $WHM_PORT: $@\n";

# Bind cPanel socket
my $cpanel_server = IO::Socket::INET->new(
    LocalPort => $CPANEL_PORT,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10
) or die "Couldn't bind cPanel port $CPANEL_PORT: $@\n";

# Bind Webmail socket
my $webmail_server = IO::Socket::INET->new(
    LocalPort => $WEBMAIL_PORT,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10
) or die "Couldn't bind Webmail port $WEBMAIL_PORT: $@\n";

my $sel = IO::Select->new($whm_server, $cpanel_server, $webmail_server);

print "Listening on ports $CPANEL_PORT (cPanel), $WHM_PORT (WHM), and $WEBMAIL_PORT (Webmail)...\n";

while (my @ready = $sel->can_read) {
    foreach my $fh (@ready) {
        if ($fh == $whm_server) {
            my $client = $whm_server->accept();
            handle_request($client, "whm");
        }
        elsif ($fh == $cpanel_server) {
            my $client = $cpanel_server->accept();
            handle_request($client, "cpanel");
        }
        elsif ($fh == $webmail_server) {
            my $client = $webmail_server->accept();
            handle_request($client, "webmail");
        }
    }
}

sub handle_request {
    my ($client, $context) = @_;
    $client->autoflush(1);
    
    my $request_line = <$client>;
    return unless $request_line;
    
    my ($method, $path, $protocol) = split(/\s+/, $request_line);
    
    # Read headers
    my %headers;
    while(<$client>) {
        s/\r?\n$//;
        last if $_ eq "";
        if (my ($key, $val) = split(/:\s*/, $_, 2)) {
            $headers{lc($key)} = $val;
        }
    }
    
    print "[$context] Handle request: $method $path\n";
    
    if ($context eq "whm") {
        route_whm($client, $path, $method);
    } elsif ($context eq "cpanel") {
        route_cpanel($client, $path, $method);
    } elsif ($context eq "webmail") {
        route_webmail($client, $path, $method);
    }
    
    close $client;
}

sub route_whm {
    my ($client, $path, $method) = @_;
    
    if ($path =~ m|^/login| && $method eq 'POST') {
        # Generate a mock session ID
        my $mock_session = "1234567890";
        my $redirect = "HTTP/1.1 302 Found\r\nLocation: /cpsess$mock_session/scripts/command?action=list_accounts\r\n\r\n";
        print $client $redirect;
        return;
    }
    
    if ($path =~ m|^/cpsess([0-9a-zA-Z]+)/scripts/command|) {
        my $session = $1;
        my $action = ($path =~ /\?action=([a-zA-Z_]+)/) ? $1 : "home";
        
        my $content = "";
        
        if ($action eq "list_accounts") {
            my $t = HTML::Template->new(filename => 'whostmgr/docroot/templates/list_accounts.tmpl', die_on_bad_params => 0);
            $t->param(session_id => $session);
            $content = $t->output();
        } elsif ($action eq "create_account") {
            my $t = HTML::Template->new(filename => 'whostmgr/docroot/templates/create_account.tmpl', die_on_bad_params => 0);
            $t->param(session_id => $session);
            $content = $t->output();
        } else {
            $content = "<h2>Welcome to WHM Dashboard</h2><p>Select an option from the sidebar.</p>";
        }
        
        my $master = HTML::Template->new(filename => 'whostmgr/docroot/templates/master.tmpl', die_on_bad_params => 0);
        $master->param(content => $content, session_id => $session, user => "root");
        
        send_response($client, 200, "text/html", $master->output());
        
    } elsif ($path eq '/' || $path =~ m|^/login|) {
        my $login_html = get_login_page("WebHost Manager", "root");
        send_response($client, 200, "text/html", $login_html);
    } else {
        send_response($client, 404, "text/plain", "WHM Resource Not Found");
    }
}

sub route_cpanel {
    my ($client, $path, $method) = @_;
    
    if ($path =~ m|^/login| && $method eq 'POST') {
        my $mock_session = "1234567890";
        my $redirect = "HTTP/1.1 302 Found\r\nLocation: /cpsess$mock_session/frontend/paper_lantern/index.html\r\n\r\n";
        print $client $redirect;
        return;
    }
    
    if ($path =~ m|^/cpsess([0-9a-zA-Z]+)/frontend/[^/]+/filemanager/index.html|) {
        my $session = $1;
        eval {
            require CpanelAPI;
            my $json_res = CpanelAPI->execute('uapi', 'Fileman', 'list_files', { dir => '/' });
            my $data = from_json($json_res);
            my $files = $data->{data}->{files} || [];
            
            my $t = HTML::Template->new(filename => 'cpanel/docroot/templates/filemanager.tmpl', die_on_bad_params => 0);
            $t->param(user => "exampleuser", current_path => "/home/exampleuser/", files => $files);
            send_response($client, 200, "text/html", $t->output());
        };
        if ($@) {
            send_response($client, 500, "text/plain", "Template Error: $@");
        }
    } elsif ($path =~ m|^/cpsess([0-9a-zA-Z]+)/frontend/[^/]+/index.html|) {
        my $session = $1;
        eval {
            my $t = HTML::Template->new(filename => 'cpanel/docroot/templates/master.tmpl', die_on_bad_params => 0);
            $t->param(user => "exampleuser", domain => "example.com", session_id => $session);
            send_response($client, 200, "text/html", $t->output());
        };
        if ($@) {
            send_response($client, 500, "text/plain", "Template Error: $@");
        }
    } elsif ($path eq '/' || $path =~ m|^/login|) {
        my $login_html = get_login_page("cPanel", "username");
        send_response($client, 200, "text/html", $login_html);
    } else {
        send_response($client, 404, "text/plain", "cPanel Resource Not Found");
    }
}

sub route_webmail {
    my ($client, $path, $method) = @_;
    
    if ($path =~ m|^/login| && $method eq 'POST') {
        my $mock_session = "1234567890";
        my $redirect = "HTTP/1.1 302 Found\r\nLocation: /cpsess$mock_session/webmail\r\n\r\n";
        print $client $redirect;
        return;
    }
    
    if ($path =~ m|^/cpsess([0-9a-zA-Z]+)/webmail|) {
        my $session = $1;
        eval {
            my $t = HTML::Template->new(filename => 'cpanel/docroot/templates/webmail.tmpl', die_on_bad_params => 0);
            $t->param(session_id => $session);
            send_response($client, 200, "text/html", $t->output());
        };
        if ($@) {
            send_response($client, 500, "text/plain", "Template Error: $@");
        }
    } elsif ($path eq '/' || $path =~ m|^/login|) {
        my $login_html = get_login_page("Webmail", "email\@domain.com");
        send_response($client, 200, "text/html", $login_html);
    } else {
        send_response($client, 404, "text/plain", "Webmail Resource Not Found");
    }
}

sub send_response {
    my ($client, $code, $content_type, $body) = @_;
    print $client "HTTP/1.1 $code OK\r\n";
    print $client "Content-Type: $content_type\r\n";
    print $client "Connection: close\r\n";
    print $client "\r\n";
    print $client $body;
}

sub get_login_page {
    my ($branding, $default_user) = @_;
    return <<"HTML";
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HostingSignal $branding</title>
    <style>
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f0f2f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background-color: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            color: #ff6b2b;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .input-group {
            margin-bottom: 20px;
            text-align: left;
        }
        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .input-group input:focus {
            outline: none;
            border-color: #ff6b2b;
        }
        .btn {
            background-color: #ff6b2b;
            color: white;
            padding: 14px;
            border: none;
            border-radius: 4px;
            width: 100%;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .btn:hover {
            background-color: #e55c20;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">HostingSignal</div>
        <div class="subtitle">Log in to $branding</div>
        
        <form method="POST" action="/login">
            <div class="input-group">
                <label for="user">Username</label>
                <input type="text" id="user" name="user" placeholder="$default_user" required>
            </div>
            
            <div class="input-group">
                <label for="pass">Password</label>
                <input type="password" id="pass" name="pass" required>
            </div>
            
            <button type="submit" class="btn">Log in</button>
        </form>
        
        <div class="footer">
            &copy; 2026 HostingSignal. All rights reserved.
        </div>
    </div>
</body>
</html>
HTML
}
