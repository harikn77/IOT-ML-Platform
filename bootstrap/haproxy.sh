#!/bin/bash
sudo apt update & sudo apt install haproxy -y
cat > /etc/haproxy/haproxy.cfg <<EOF
global
	log 127.0.0.1 local0 notice
	maxconn 2000
	user haproxy
	group haproxy

defaults
	log     global
	mode    http
	option  httplog
	option  dontlognull
	retries 3
	option redispatch
	timeout connect  5000
	timeout client  10000
	timeout server  10000

frontend deployer_service
	bind 127.0.0.1:9898
	default_backend deployers
backend deployers
	balance roundrobin
EOF
