import os
import subprocess
import argparse
import time

DATA_DIR = './data'

def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

def wait_for_api():
    """Wait until signal-cli-rest-api is fully up."""
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(
                ['docker', 'exec', 'signal-cli-rest-api', 'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:8080/v1/about'],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip() == "200":
                print("signal-cli-rest-api is up and running.")
                return True
            print(f"API not ready yet, attempt {attempt + 1}/{max_attempts}...")
        except Exception as e:
            print(f"Waiting for API, attempt {attempt + 1}/{max_attempts}: {e}")
        time.sleep(3)
    print("Failed to verify signal-cli-rest-api after 10 attempts.")
    return False

def is_linked():
    """Check if the bot is linked using the D-Bus interface inside the signal-cli-rest-api container."""
    try:
        # Start signal-cli-rest-api first if not already running
        subprocess.check_call(['docker-compose', 'up', '-d', 'signal-cli-rest-api'])
        if not wait_for_api():
            print("signal-cli-rest-api failed to start properly.")
            return False

        # Define a Python script to check D-Bus status
        check_script = """
import dbus
try:
    bus = dbus.SessionBus()
    service_names = bus.list_names()
    if "org.asamk.Signal" in service_names:
        service = bus.get_object("org.asamk.Signal", "/")
        interface = dbus.Interface(service, "org.asamk.Signal")
        registered = interface.isRegistered()
        connected = interface.isConnected()
        if registered and connected:
            print("Linked")
        else:
            print("Not linked")
    else:
        print("Not linked")
except Exception as e:
    print(f"Error: {e}")
"""
        # Write the script to a temporary file
        with open('check_dbus.py', 'w') as f:
            f.write(check_script)

        # Copy the script into the container
        subprocess.check_call(['docker', 'cp', 'check_dbus.py', 'signal-cli-rest-api:/check_dbus.py'])

        # Run the script inside the container
        result = subprocess.run(
            ['docker', 'exec', 'signal-cli-rest-api', 'python3', '/check_dbus.py'],
            capture_output=True, text=True
        )

        # Clean up temporary files
        os.remove('check_dbus.py')
        subprocess.run(['docker', 'exec', 'signal-cli-rest-api', 'rm', '/check_dbus.py'])

        # Check the result
        if "Linked" in result.stdout:
            print("Signal-bot is linked.")
            return True
        else:
            print("Signal-bot is not linked.")
            return False
    except Exception as e:
        print(f"Error checking linking status: {e}")
        return False
    finally:
        subprocess.check_call(['docker-compose', 'stop', 'signal-cli-rest-api'])

def link_signal_cli():
    """Start signal-cli-rest-api in normal mode for initial linking."""
    ensure_data_dir()
    print("Starting signal-cli-rest-api in normal mode for linking...")
    env = os.environ.copy()
    env['MODE'] = 'normal'
    subprocess.check_call(['docker-compose', 'up', '-d', 'signal-cli-rest-api'], env=env)
    print("Please check the logs for the QR code: docker logs signal-cli-rest-api")
    print("Scan the QR code with your Signal app to link the device.")
    input("Press Enter after linking is complete...")
    subprocess.check_call(['docker-compose', 'down'])
    print("Linking complete.")

def start_application():
    """Start all Docker containers after ensuring linking is done."""
    ensure_data_dir()
    if not is_linked():
        print("Signal bot is not linked. Initiating linking process...")
        link_signal_cli()
    print("Starting Docker containers...")
    subprocess.check_call(['docker-compose', 'up', '--build', '-d'])

def stop_application():
    """Stop all Docker containers."""
    print("Stopping Docker containers...")
    subprocess.check_call(['docker-compose', 'down'])

def main():
    parser = argparse.ArgumentParser(description="Manage Signal Bot Application")
    parser.add_argument('action', choices=['link', 'start', 'stop'], help="Action to perform")
    args = parser.parse_args()

    if args.action == 'link':
        link_signal_cli()
    elif args.action == 'start':
        start_application()
    elif args.action == 'stop':
        stop_application()

if __name__ == '__main__':
    main()