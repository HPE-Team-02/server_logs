def search_log_for_uuid(log_file, uuids):
    """Search the log file for occurrences of 'task queue details of the firmware update on server <uuid>' and filter results."""
    if not os.path.exists(log_file):
        print(f"Error: Log file '{log_file}' not found.")
        return
    
    with open(log_file, 'r', encoding='utf-8') as file:
        log_content = file.readlines()
    
    pattern = re.compile(r"task queue details of the firmware update on server (\S+)")
    matches = []
    
    for line in log_content:
        match = pattern.search(line)
        if match and match.group(1) in uuids:
            matches.append(line.strip())
    
    filtered_matches = filter_valid_matches(matches)
    
    server_details = []
    for match in filtered_matches:
        details = parse_members_from_match(match)
        if details:
            server_details.extend(details)  # Append all extracted details
    
    for details in server_details:
        print(f"\nServer Details: {details}\n")
    
    return server_details