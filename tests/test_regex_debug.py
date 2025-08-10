#!/usr/bin/env python3
"""
Debug dei pattern regex.
"""

import re

# Test pattern CEF
cef_pattern = r'^CEF:(?P<version>\d+)\|(?P<device_vendor>[^|]*)\|(?P<device_product>[^|]*)\|(?P<device_version>[^|]*)\|(?P<device_event_class_id>[^|]*)\|(?P<name>[^|]*)\|(?P<severity>[^|]*)\|(?P<extension>.*)$'
cef_test = "CEF:0|Fortinet|FortiGate|v6.0.0|0000000013|virus detected|1|src=192.168.1.100 dst=10.0.0.1"

# Test pattern IP
ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
ip_test = "192.168.1.100"

# Test pattern Apache
apache_pattern = r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]*)" (?P<status>\d+) (?P<bytes>\S+)'
apache_test = '192.168.1.100 - - [25/Dec/2023:10:30:45 +0000] "GET /index.html HTTP/1.1" 200 2326'

print("🧪 Debug pattern regex:")
print()

# Test CEF
print("📋 Test CEF:")
print(f"   Pattern: {cef_pattern}")
print(f"   Test: {cef_test}")
compiled_cef = re.compile(cef_pattern)
match = compiled_cef.search(cef_test)
if match:
    print(f"   ✅ Match trovato: {match.groupdict()}")
else:
    print("   ❌ Nessun match")
print()

# Test IP
print("📋 Test IP:")
print(f"   Pattern: {ip_pattern}")
print(f"   Test: {ip_test}")
compiled_ip = re.compile(ip_pattern)
match = compiled_ip.search(ip_test)
if match:
    print(f"   ✅ Match trovato: {match.group()}")
else:
    print("   ❌ Nessun match")
print()

# Test Apache
print("📋 Test Apache:")
print(f"   Pattern: {apache_pattern}")
print(f"   Test: {apache_test}")
compiled_apache = re.compile(apache_pattern)
match = compiled_apache.search(apache_test)
if match:
    print(f"   ✅ Match trovato: {match.groupdict()}")
else:
    print("   ❌ Nessun match") 