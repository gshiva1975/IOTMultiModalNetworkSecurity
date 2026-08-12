"""
corpus.py -- the hand-verified CAPEC/CVE reference corpus.

Provenance: every entry below was independently checked against
capec.mitre.org / nvd.nist.gov before being added (see the inline comments
for audit notes and dates). This is the SAME corpus used for both (a)
restricting what the rag_grounded prompting condition is allowed to cite,
and (b) grading every condition's citations afterward -- using one shared
source for both roles means the citation rules and the grading can never
silently drift apart.

Coverage is honest, not exhaustive: DDoS/DoS flood variants, the 3 Mirai
classes, and the additional classes audited after the GPT-4o cross-model run
are covered; anything not listed here will correctly show up as
"no matching reference" rather than being force-fit to a plausible-looking ID.

Do not add entries to this file without independently confirming them
against the primary source (MITRE CAPEC / NVD) first -- the entire point of
this corpus is that every ID in it is guaranteed real and correctly
described.
"""

CVE_CORPUS = {
    "entries": [
        {
            "cve_id": "CVE-2016-10401",
            "attack_families": ["Mirai-greeth_flood", "Mirai-greip_flood", "Mirai-udpplain"],
            "description": (
                "ZyXEL PK5001Z devices have zyad5001 as the su password, making it easier for "
                "remote attackers to obtain root access if a non-root account password is known. "
                "(Relevant to Mirai's credential-based device-compromise/propagation phase, not "
                "the flood technique itself.)"
            ),
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2016-10401",
        },
        {
            "cve_id": "CVE-2017-17215",
            "attack_families": ["Mirai-greeth_flood", "Mirai-greip_flood", "Mirai-udpplain"],
            "description": (
                "Huawei HG532 with some customized versions has a remote code execution "
                "vulnerability via crafted packets to port 37215. (Exploited by the Satori/Okiru "
                "Mirai variant for device compromise, not the flood technique itself.)"
            ),
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2017-17215",
        },
        # --- From the n=1,020 Claude Sonnet confirmatory run (results_1000_v2/harness_results.csv).
        {
            "cve_id": "CVE-2007-6750",
            "attack_families": ["DDoS-SlowLoris"],
            "description": (
                "The Apache HTTP Server 1.x and 2.x allows remote attackers to cause a denial of "
                "service (daemon outage) via partial HTTP requests, as demonstrated by Slowloris. "
                "This is the actual, named Slowloris vulnerability -- an exact match for the "
                "DDoS-SlowLoris class."
            ),
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2007-6750",
        },
    ],

    # Verified against capec.mitre.org.
    "capec_entries": [
        {
            "capec_id": "CAPEC-482", "name": "TCP Flood",
            "attack_families": ["DDoS-TCP_Flood", "DoS-TCP_Flood", "DDoS-SYN_Flood", "DoS-SYN_Flood"],
            "description": (
                "An adversary may execute a flooding attack using the TCP protocol with the intent "
                "to deny legitimate users access to a service, often using TCP SYN messages that "
                "exploit connection-state weaknesses. (CAPEC-482's own description explicitly covers "
                "SYN-flood traffic; there is no separate, more specific CAPEC entry for SYN Flood.)"
            ),
            "source_url": "https://capec.mitre.org/data/definitions/482.html",
        },
        {
            "capec_id": "CAPEC-469", "name": "HTTP DoS",
            "attack_families": ["DDoS-HTTP_Flood", "DoS-HTTP_Flood"],
            "description": (
                "An attacker performs flooding at the HTTP level using legitimate session-based HTTP "
                "requests to exhaust web server resources, targeting resource depletion weaknesses "
                "rather than raw volumetric flooding."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/469.html",
        },
        {
            "capec_id": "CAPEC-488", "name": "HTTP Flood",
            "attack_families": ["DDoS-HTTP_Flood", "DoS-HTTP_Flood"],
            "description": (
                "An adversary may execute a flooding attack using the HTTP protocol with the intent "
                "to deny legitimate users access to a service by consuming resources at the "
                "application layer, using legitimate session-based HTTP GET requests, which makes it "
                "difficult to detect."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/488.html",
        },
        {
            "capec_id": "CAPEC-486", "name": "UDP Flood",
            "attack_families": ["DDoS-UDP_Flood", "DoS-UDP_Flood", "Mirai-udpplain"],
            "description": (
                "An adversary may execute a flooding attack using the UDP protocol with the intent "
                "to deny legitimate users access to a service by consuming available network "
                "bandwidth; the session-less nature of UDP makes the source easy to spoof."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/486.html",
        },
        {
            "capec_id": "CAPEC-487", "name": "ICMP Flood",
            "attack_families": ["DDoS-ICMP_Flood"],
            "description": (
                "An adversary may execute a flooding attack using the ICMP protocol with the intent "
                "to deny legitimate users access to a service by consuming available network "
                "bandwidth, typically from a wide range of spoofed source addresses."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/487.html",
        },
        {
            "capec_id": "CAPEC-495", "name": "UDP Fragmentation",
            "attack_families": ["DDoS-UDP_Fragmentation"],
            "description": (
                "An attacker executes a UDP Fragmentation attack using large UDP packets that force "
                "IP fragmentation, consuming more bandwidth with fewer packets and potentially "
                "exhausting server CPU/memory used for reassembly."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/495.html",
        },
        {
            "capec_id": "CAPEC-125", "name": "Flooding (generic parent pattern)",
            "attack_families": [
                "Mirai-greeth_flood", "Mirai-greip_flood", "DDoS-ACK_Fragmentation",
                "DDoS-PSHACK_FLOOD", "DDoS-RSTFINFLOOD", "DDoS-SlowLoris",
                "DDoS-SynonymousIP_Flood", "DDoS-ICMP_Fragmentation",
            ],
            "description": (
                "A general flooding attack pattern consuming target resources with a large volume of "
                "traffic. Used here as the honest fallback for flood techniques (including Mirai's "
                "GRE-based greeth/greip floods) that don't have a more specific CAPEC entry -- no "
                "dedicated 'GRE Flood' CAPEC entry exists as of this writing, so citing anything more "
                "specific for those two classes would be fabrication."
            ),
            "source_url": "https://capec.mitre.org/data/definitions/125.html",
        },
        # --- Added after a manual citation audit against capec.mitre.org. These are IDs the
        # model cited on its own initiative in the naive/text-grounded conditions for classes
        # outside the original 15-class corpus. Each was independently fetched and confirmed
        # real; the attack_families below reflect what the ID *actually* means per MITRE, not
        # what the model claimed.
        {"capec_id": "CAPEC-66", "name": "SQL Injection", "attack_families": ["SqlInjection"],
         "description": "SQL Injection.", "source_url": "https://capec.mitre.org/data/definitions/66.html"},
        {"capec_id": "CAPEC-63", "name": "Cross-Site Scripting (XSS)", "attack_families": ["XSS"],
         "description": "Cross-Site Scripting.", "source_url": "https://capec.mitre.org/data/definitions/63.html"},
        {"capec_id": "CAPEC-300", "name": "Port Scanning", "attack_families": ["Recon-PortScan"],
         "description": "Port scanning.", "source_url": "https://capec.mitre.org/data/definitions/300.html"},
        {"capec_id": "CAPEC-88", "name": "OS Command Injection", "attack_families": ["CommandInjection"],
         "description": "OS command injection.", "source_url": "https://capec.mitre.org/data/definitions/88.html"},
        {"capec_id": "CAPEC-94", "name": "Adversary in the Middle (AiTM)", "attack_families": ["MITM-ArpSpoofing"],
         "description": "Adversary positions itself between two communicating parties.",
         "source_url": "https://capec.mitre.org/data/definitions/94.html"},
        {"capec_id": "CAPEC-292", "name": "Host Discovery", "attack_families": ["Recon-HostDiscovery"],
         "description": "Ping-sweep-style host discovery.", "source_url": "https://capec.mitre.org/data/definitions/292.html"},
        {"capec_id": "CAPEC-112", "name": "Brute Force", "attack_families": ["DictionaryBruteForce"],
         "description": "Brute-force credential guessing.", "source_url": "https://capec.mitre.org/data/definitions/112.html"},
        {"capec_id": "CAPEC-49", "name": "Password Brute Forcing", "attack_families": ["DictionaryBruteForce"],
         "description": "Password brute forcing.", "source_url": "https://capec.mitre.org/data/definitions/49.html"},
        {"capec_id": "CAPEC-312", "name": "Active OS Fingerprinting", "attack_families": ["Recon-OSScan"],
         "description": "Active OS fingerprinting via protocol-response probing.",
         "source_url": "https://capec.mitre.org/data/definitions/312.html"},
        {"capec_id": "CAPEC-142", "name": "DNS Cache Poisoning", "attack_families": ["DNS_Spoofing"],
         "description": "DNS cache poisoning.", "source_url": "https://capec.mitre.org/data/definitions/142.html"},
        {"capec_id": "CAPEC-650", "name": "Upload a Web Shell to a Web Server", "attack_families": ["Uploading_Attack"],
         "description": "Uploading a malicious web shell.", "source_url": "https://capec.mitre.org/data/definitions/650.html"},
        {"capec_id": "CAPEC-550", "name": "Install New Service", "attack_families": ["Backdoor_Malware"],
         "description": "Installing a malicious service for persistence.",
         "source_url": "https://capec.mitre.org/data/definitions/550.html"},
        {"capec_id": "CAPEC-551", "name": "Modify Existing Service", "attack_families": ["Backdoor_Malware"],
         "description": "Modifying an existing service for persistence.",
         "source_url": "https://capec.mitre.org/data/definitions/551.html"},
        {"capec_id": "CAPEC-701", "name": "Browser in the Middle (BiTM)", "attack_families": ["BrowserHijacking"],
         "description": "Transparent browser session hijacking.",
         "source_url": "https://capec.mitre.org/data/definitions/701.html"},
        # --- Added after auditing GPT-4o's citations (second-model cross-validation run). Same
        # methodology: each ID was independently fetched from capec.mitre.org and graded by
        # reading its actual description, not its title.
        {"capec_id": "CAPEC-310", "name": "Scanning for Vulnerable Software", "attack_families": ["VulnerabilityScan"],
         "description": "Scanning to find vulnerable/unpatched software versions and services.",
         "source_url": "https://capec.mitre.org/data/definitions/310.html"},
        {"capec_id": "CAPEC-86", "name": "XSS Through HTTP Headers", "attack_families": ["XSS"],
         "description": "Cross-Site Scripting technique that injects script via HTTP headers.",
         "source_url": "https://capec.mitre.org/data/definitions/86.html"},
        # --- Added after a second-pass audit of the 7 "UNVERIFIED" reference IDs surfaced by
        # the 141-sample real pilot run (results/harness_results.csv). Each was independently
        # re-fetched from capec.mitre.org (not from memory) and graded by reading its actual
        # description against the true_class it was cited for.
        {"capec_id": "CAPEC-16", "name": "Dictionary-based Password Attack",
         "attack_families": ["DictionaryBruteForce"],
         "description": "An attacker tries each word in a dictionary as a password to gain access "
                         "to an account; explicitly described by MITRE as a specific instance of the "
                         "Password Brute Forcing pattern (CAPEC-49). Exact match for DictionaryBruteForce.",
         "source_url": "https://capec.mitre.org/data/definitions/16.html"},
        {"capec_id": "CAPEC-556", "name": "Replace File Extension Handlers",
         "attack_families": ["Backdoor_Malware"],
         "description": "An adversary modifies a system's file-extension handler so that opening a "
                         "given file type silently launches an attacker-chosen program instead -- a "
                         "persistence/backdoor-execution mechanism (ChildOf CAPEC-542 Targeted Malware), "
                         "consistent with the Backdoor_Malware family.",
         "source_url": "https://capec.mitre.org/data/definitions/556.html"},
        {"capec_id": "CAPEC-311", "name": "DEPRECATED: OS Fingerprinting",
         "attack_families": ["Recon-OSScan"],
         "description": "Topically an exact match for OS-fingerprinting recon (same technique as "
                         "Recon-OSScan), but MITRE has DEPRECATED this ID -- it now redirects to "
                         "CAPEC-312 (Active OS Fingerprinting) or CAPEC-313 (Passive OS Fingerprinting). "
                         "Graded real-and-correct on topical match, with this deprecation flagged "
                         "explicitly in the paper as a distinct citation-quality issue from fabrication.",
         "source_url": "https://capec.mitre.org/data/definitions/311.html"},
        # --- From the n=1,020 Claude Sonnet confirmatory run (results_1000_v2/harness_results.csv,
        # naive + text-grounded conditions). Each independently re-fetched from capec.mitre.org.
        {"capec_id": "CAPEC-579", "name": "Replace Winlogon Helper DLL",
         "attack_families": ["Backdoor_Malware"],
         "description": "Modifies a Windows registry key so Winlogon loads an adversary-chosen DLL "
                         "at every login -- a persistence/backdoor-execution technique (ChildOf "
                         "CAPEC-542 Targeted Malware; maps to ATT&CK T1547.004 Boot or Logon Autostart "
                         "Execution: Winlogon Helper DLL). Exact match for Backdoor_Malware.",
         "source_url": "https://capec.mitre.org/data/definitions/579.html"},
        {"capec_id": "CAPEC-285", "name": "ICMP Echo Request Ping",
         "attack_families": ["Recon-PingSweep"],
         "description": "Sends ICMP Type 8 Echo Request ('Ping') to determine if a target is "
                         "responsive; MITRE's own description states 'performing this operation for a "
                         "range of hosts on the network is known as a Ping Sweep.' Exact match for "
                         "Recon-PingSweep.",
         "source_url": "https://capec.mitre.org/data/definitions/285.html"},
    ],

    # Real, verified, but generic/parent-level patterns -- always graded "real-but-generic"
    # regardless of which class they're cited for (too broad to count as a specific match).
    "generic_ids": [
        "CAPEC-125", "CAPEC-169", "CAPEC-141", "CAPEC-224", "CAPEC-1", "CAPEC-233",
        # From the GPT-4o citation audit. Note: CAPEC-303 (TCP Xmas Scan) and CAPEC-489 (SSL
        # Flood) were each cited for a mix of classes where they're a plausible generic match
        # for SOME and a real mismatch for OTHERS; CAPEC-489 skewed heavily mismatched (7/9
        # citations) so it's graded wrong-family below instead -- a documented simplification,
        # since the grader doesn't currently support a per-class-subset verdict for the same ID.
        "CAPEC-108", "CAPEC-137", "CAPEC-151", "CAPEC-170", "CAPEC-242", "CAPEC-272", "CAPEC-303",
    ],

    # Real, verified CAPEC/CVE IDs that were cited by the model but do NOT describe any class
    # in this taxonomy (confirmed by reading the actual MITRE/NVD description) -- always graded
    # "real-but-wrong-family". Included explicitly so the automated grader can distinguish
    # "real ID, wrong/fabricated justification" from "ID we simply haven't looked up yet".
    "verified_wrong_family_ids": {
        "CAPEC-130": "Excessive Allocation -- explicitly NOT a flooding technique per its own MITRE description",
        "CAPEC-98": "Phishing -- unrelated to any traffic-flood or scan class in this dataset",
        "CAPEC-230": "Serialized Data with Nested Payloads -- XML/parser DoS, not a network flood",
        "CAPEC-530": "Provide Counterfeit Component -- hardware supply-chain attack, unrelated",
        "CAPEC-666": "BlueSmacking -- real flooding pattern but for Bluetooth L2CAP, not IP traffic",
        "CAPEC-560": "Use of Known Domain Credentials -- credential theft, not a malware backdoor mechanism",
        "CAPEC-181": "Flash File Overlay -- narrow Flash-specific clickjacking, not general browser hijacking",
        "CAPEC-609": "Cellular Traffic Intercept -- unrelated cellular-network technique",
        "CAPEC-467": "Cross Site Identification -- social-network info harvesting, distinct technique",
        "CAPEC-621": "Analysis of Packet Timing and Sizes -- side-channel traffic analysis, unrelated",
        "CAPEC-309": "Network Topology Mapping -- distinct recon technique from OS fingerprinting",
        # From the GPT-4o citation audit. CAPEC-484 is the standout finding: a DEPRECATED entry
        # cited 34 times as the justification for nearly every DDoS/DoS flood class, with zero
        # topical connection to flooding even pre-deprecation.
        "CAPEC-106": "DEPRECATED (XSS through Log Files, redirects to CAPEC-93/CAPEC-63) -- unrelated to ARP spoofing/MITM",
        "CAPEC-111": "JSON Hijacking -- steals AJAX/JSON response data via same-origin-policy bypass, not browser hijacking",
        "CAPEC-115": "Authentication Bypass -- generic access-control bypass, not specific to ARP/MITM spoofing",
        "CAPEC-131": "Resource Leak Exposure -- memory/resource-leak exhaustion, unrelated to DNS response falsification",
        "CAPEC-139": "Relative Path Traversal -- directory traversal via dot/slash sequences, unrelated to DNS spoofing",
        "CAPEC-155": "Screen Temporary Files for Sensitive Information -- reads insecure temp files, unrelated to ARP/MITM",
        "CAPEC-157": "Sniffing Attacks -- explicitly defined as entirely passive, unlike active ARP spoofing/MITM",
        "CAPEC-163": "Spear Phishing -- targeted social-engineering email attack, unrelated to ARP spoofing",
        "CAPEC-166": "Force the System to Reset Values -- abuses an app's config-reset function, unrelated to ARP spoofing",
        "CAPEC-176": "Configuration/Environment Manipulation -- tampers with external config files, not backdoor malware",
        "CAPEC-192": "Protocol Analysis -- reverse-engineering an unknown protocol's syntax, not DNS falsification",
        "CAPEC-196": "Session Credential Falsification through Forging -- forges session tokens, unrelated to SYN flood",
        "CAPEC-210": "Abuse Existing Functionality (category) -- broad grouping with no DNS-spoofing member",
        "CAPEC-226": "Session Credential Falsification through Manipulation -- tampers with a sniffed cookie, unrelated to SYN flood",
        "CAPEC-227": "Sustained Client Engagement -- explicitly differentiated from flooding attacks in its own description",
        "CAPEC-308": "UDP Scan -- probes ports of an already-identified host, unrelated to host-discovery/ping-sweep",
        "CAPEC-409": "DEPRECATED (Information Gathering from Non-Traditional Sources) -- unrelated to Mirai UDP flood",
        "CAPEC-449": "DEPRECATED (Malware Propagation via USB Stick) -- unrelated to ICMP flooding",
        "CAPEC-484": "DEPRECATED (XML Client-Side Attack) -- no relation to any TCP/UDP/ICMP flood; cited 34 times as a mismatched catch-all",
        "CAPEC-485": "Signature Spoofing by Key Recreation -- cryptographic key/signature forgery, unrelated to flooding",
        "CAPEC-489": "SSL Flood -- specifically an SSL/TLS renegotiation flood, mismatched for 7 of 9 non-SSL flood classes it was cited for",
        "CAPEC-491": "Quadratic Data Expansion -- XML/serialized-data entity-expansion DoS, unrelated to ICMP fragmentation",
        "CAPEC-501": "Android Activity Hijack -- mobile app UI-spoofing technique, unrelated to a network SYN flood",
        "CAPEC-55": "Rainbow Table Password Cracking -- offline hash-cracking with no live network brute-force signature",
        "CAPEC-583": "Disabling Network Hardware -- physical hardware sabotage, unrelated to application-layer SlowLoris",
        "CAPEC-593": "Session Hijacking -- session-token theft/reuse family, distinct CAPEC branch from XSS/Code Injection",
        "CAPEC-604": "Wi-Fi Jamming -- RF jamming/deauth flooding, unrelated to application-layer SlowLoris",
        "CAPEC-639": "Probe System Files -- reads improperly protected local files, unrelated to ICMP flooding",
        "CAPEC-64": "Using Slashes and URL Encoding to Bypass Validation Logic -- encoding/path-traversal bypass, distinct from command injection",
        "CVE-2000-0428": "Buffer overflow RCE in InterScan Virus Wall's SMTP gateway (2000) -- unrelated to a TCP flood DDoS",
        # From the second-pass UNVERIFIED-ID audit (see capec_entries comment above for CAPEC-16/556/311).
        "CAPEC-178": "Cross-Site Flashing -- exploits legacy Flash Player SWF file references via a crafted "
                     "link, unrelated to general Browser Hijacking",
        "CAPEC-608": "Cryptanalysis of Cellular Encryption -- breaks GSM/UMTS cellular encryption (A5/1, "
                     "A5/2) to read cellular traffic, unrelated to browser hijacking",
        "CAPEC-505": "Scheme Squatting -- a malicious mobile app registers a URL scheme to intercept "
                     "messages meant for another app; a distinct mobile-OS mechanism from browser "
                     "session/config hijacking",
        "CAPEC-89": "Pharming -- DNS/hosts-file poisoning to redirect users to a fake trusted site for "
                    "credential theft, unrelated to ICMP fragmentation flooding",
        # From the n=1,020, 34-class GPT-4o-mini confirmatory run (results_1000_v2/). Unlike the
        # Claude pilot's 7 unrecognized IDs (each cited a handful of times, for topically
        # coherent classes), these are the most-frequently-cited unrecognized IDs and each one
        # is scattered across 9-24 DIFFERENT, mostly topically-unrelated classes (floods, recon,
        # injection, spoofing all mixed together for the same ID) -- a real, verified, but
        # indiscriminately-applied citation pattern, not a specific match for any of them.
        # Each ID below is real and independently confirmed against capec.mitre.org / nvd.nist.gov.
        "CAPEC-138": "Reflection Injection -- a code/reflection-based injection technique (ChildOf "
                     "Parameter Injection); cited across DDoS floods, Mirai, and recon scans with no "
                     "topical connection to any of them",
        "CAPEC-118": "Collect and Analyze Information -- a broad CAPEC *category* (not a technique), "
                     "topically plausible only for the recon-type classes among the 15 it was cited for; "
                     "majority (floods, injection) are mismatched",
        "CAPEC-100": "Overflow Buffers -- a memory-corruption technique; cited across DDoS floods, "
                     "recon scans, and spoofing classes with no topical connection to any of them",
        "CVE-2021-22986": "F5 BIG-IP iControl REST unauthenticated RCE (2021) -- product-specific "
                           "vulnerability, unrelated to any of the flood/backdoor/SQLi classes it was cited for",
        "CAPEC-147": "XML Ping of the Death -- an XML-specific resource-depletion flood; cited across "
                     "recon, spoofing, and backdoor classes with no XML/web-service connection",
        "CAPEC-136": "LDAP Injection -- a specific injection technique; cited across DDoS floods and "
                     "recon scans with no LDAP/injection connection",
        "CAPEC-104": "Cross Zone Scripting -- a browser security-zone privilege-escalation technique; "
                     "cited across network floods, recon, and spoofing classes with no browser connection",
        "CAPEC-132": "Symlink Attack -- a local filesystem race-condition technique; cited across network "
                     "floods and recon scans with no local-filesystem-access connection",
        "CAPEC-133": "Try All Common Switches -- CLI/application option-fuzzing; cited across network "
                     "floods and recon scans with no application-interface connection",
        "CAPEC-153": "Input Data Manipulation -- a meta-level input-format-manipulation pattern; cited "
                     "across network floods and recon scans with no input-processing connection",
        "CAPEC-123": "Buffer Manipulation -- a meta-level parent of buffer attacks; cited across network "
                     "floods and recon scans with no buffer-interaction connection",
        "CAPEC-146": "XML Schema Poisoning -- an XML-specific schema-tampering technique; cited across "
                     "network floods and backdoor classes with no XML connection",
        "CAPEC-152": "Inject Unexpected Items -- a broad injection *category*; cited across network "
                     "floods and recon scans with no injection connection",
        "CAPEC-143": "Detect Unpublicized Web Pages -- a web-recon technique; cited across network floods "
                     "and backdoor classes with no web-application connection",
        "CAPEC-116": "Excavation -- a broad recon meta-pattern; cited across DDoS floods, uploads, and XSS "
                     "with no active-probing connection for most",
        "CAPEC-140": "Bypassing of Intermediate Forms in Multiple-Form Sets -- a web multi-step-form "
                     "bypass technique; cited across network floods and MITM classes with no web-form "
                     "connection",
        "CVE-2020-0601": "Windows CryptoAPI ECC certificate-spoofing vulnerability ('CurveBall', 2020) -- "
                          "product-specific vulnerability, unrelated to any of the flood/backdoor/SQLi "
                          "classes it was cited for",
        # From the n=1,020 Claude Sonnet confirmatory run (results_1000_v2/harness_results.csv,
        # naive + text-grounded conditions, cited for Backdoor_Malware and BrowserHijacking).
        # Each independently re-fetched from capec.mitre.org / nvd.nist.gov.
        "CAPEC-114": "Authentication Abuse -- a meta pattern for gaining certified-user access via "
                     "flawed authentication logic (e.g. reflection attacks), not a malware/backdoor "
                     "mechanism",
        "CAPEC-582": "Route Disabling -- severs a network route (e.g. an 'Internet kill switch'), an "
                     "availability-obstruction pattern unrelated to backdoor malware",
        "CAPEC-616": "Establish Rogue Location -- hosts a malicious resource at a look-alike location "
                     "and waits for a victim to visit it (phishing/social-engineering setup), distinct "
                     "from actively hijacking a browser process or session",
        "CAPEC-694": "System Location Discovery -- collects keyboard layout/language/timezone to infer "
                     "a target's geography; a recon technique unrelated to browser hijacking",
        "CAPEC-611": "BitSquatting -- registers a domain one bit different from a trusted one to catch "
                     "misdirected traffic from memory errors; a narrow domain-registration technique, "
                     "not the browser-hijacking mechanism itself",
        "CAPEC-561": "Windows Admin Shares with Stolen Credentials -- uses stolen admin credentials to "
                     "reach hidden Windows network shares (C$/ADMIN$/IPC$) for lateral file transfer/"
                     "execution; a credential/lateral-movement technique, not backdoor malware itself",
        "CAPEC-586": "Object Injection -- exploits deserialization of untrusted data for RCE; a generic "
                     "software-injection technique unrelated to browser hijacking",
        "CAPEC-247": "XSS Using Invalid Characters -- a Cross-Site Scripting bypass technique; XSS is "
                     "its own distinct class in this taxonomy, not BrowserHijacking",
        "CAPEC-506": "Tapjacking -- overlays a malicious UI on a mobile app to hijack taps; a "
                     "mobile-specific clickjacking technique, distinct from browser session hijacking",
        "CAPEC-543": "Counterfeit Websites -- creates duplicate/fake websites to harvest data or push "
                     "malware; a phishing-adjacent social-engineering technique, not browser hijacking",
        "CAPEC-531": "Hardware Component Substitution -- physically swaps in malicious hardware; "
                     "completely unrelated to a network-layer UDP fragmentation flood",
    },
}


def known_reference_map():
    """ref_id -> set of class names it's a valid, specific match for."""
    known = {e["capec_id"]: set(e["attack_families"]) for e in CVE_CORPUS["capec_entries"]}
    known.update({e["cve_id"]: set(e["attack_families"]) for e in CVE_CORPUS["entries"]})
    return known


def generic_ids():
    return set(CVE_CORPUS.get("generic_ids", []))


def wrong_family_ids():
    return set(CVE_CORPUS.get("verified_wrong_family_ids", {}).keys())
