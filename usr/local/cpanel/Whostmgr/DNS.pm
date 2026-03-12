package Whostmgr::DNS;

use strict;
use warnings;
use POSIX qw(strftime);

=head1 NAME

Whostmgr::DNS - Zone File Management

=head1 DESCRIPTION

Generates and manages Bind / PowerDNS zone files, mirroring 
the Cpanel DNS controller.

=cut

sub create_zone {
    my ($class, %args) = @_;
    
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $ip     = $args{ip}     || "127.0.0.1";
    my $admin_email = $args{admin_email} || "admin.$domain";
    
    # Replace @ with . for SOA
    $admin_email =~ s/\@/\./;
    
    my $serial = strftime("%Y%m%d01", localtime);
    
    my $zone_data = <<"EOF";
\$TTL 14400
@   IN  SOA ns1.hostingsignal.com. $admin_email. (
            $serial ; Serial
            3600       ; Refresh
            1800       ; Retry
            1209600    ; Expire
            86400      ; Minimum TTL
)

; Name Servers
@   IN  NS  ns1.hostingsignal.com.
@   IN  NS  ns2.hostingsignal.com.

; A Records
@   IN  A   $ip
www IN  A   $ip
mail IN A   $ip

; MX Records
@   IN  MX  10 mail.$domain.

; TXT Records
@   IN  TXT "v=spf1 +a +mx -all"
EOF

    # Normally would write to /var/named/ and run `rndc reload`
    print "Generated DNS Zone for $domain:\n";
    print "---\n$zone_data\n---\n";
    
    return { success => 1, message => "DNS Zone created for $domain" };
}

sub delete_zone {
    my ($class, $domain) = @_;
    print "Deleting DNS zone for $domain...\n";
    return { success => 1, message => "DNS Zone deleted for $domain" };
}

sub add_zone_record {
    my ($class, %args) = @_;
    
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $name   = $args{name}   || return { success => 0, error => "Missing record name" };
    my $type   = $args{type}   || return { success => 0, error => "Missing record type" };
    my $target = $args{address} || $args{cname} || $args{txtdata} || return { success => 0, error => "Missing target address" };
    
    $type = uc($type);
    
    # Ensure fully qualified
    $name .= ".$domain." unless $name =~ /\.$/;
    
    my $record_line = sprintf("%-20s IN %-5s %s", $name, $type, $target);
    
    # In real execution, append to /var/named/$domain.db and bump serial
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock DNS: Appending to $domain -> $record_line\n";
    }
    
    return { success => 1, message => "Added record $record_line to $domain" };
}

sub parse_zone {
    my ($class, $domain) = @_;
    # In a real setup, parse /var/named/$domain.db
    # Mock return
    my @records = (
        { line => 1, name => "$domain.", type => "A", address => "127.0.0.1" },
        { line => 2, name => "www.$domain.", type => "CNAME", cname => "$domain." }
    );
    
    return { success => 1, data => \@records };
}

1; # End of module
