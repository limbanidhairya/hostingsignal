FROM perl:5.38-slim

# Install required CPAN modules (JSON is used for API responses, URI::Escape for URL encoding)
RUN cpanm --notest --quiet JSON URI::Escape

# Create runtime directories required by the panel
RUN mkdir -p /var/hspanel/users \
             /var/hspanel/queue \
             /var/hspanel/userdata \
             /usr/local/hspanel/logs

# Copy the entire hspanel directory tree (context is usr/local/hspanel)
WORKDIR /usr/local/hspanel
COPY . /usr/local/hspanel/

EXPOSE 2086

CMD ["perl", "/usr/local/hspanel/daemon/hs-srvd.pl"]
