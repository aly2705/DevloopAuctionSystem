import socket
import json
import threading
import time
import os

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class AuctionClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.name = None
        self.connected = False
        self.message_queue = []
        self.message_lock = threading.Lock()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 50}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}Welcome to the Auction System{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 50}{Colors.ENDC}\n")

    def print_menu(self):
        print(f"\n{Colors.BOLD}Menu Options:{Colors.ENDC}")
        print(f"{Colors.CYAN}1.{Colors.ENDC} View Available Products")
        print(f"{Colors.CYAN}2.{Colors.ENDC} Add New Product")
        print(f"{Colors.CYAN}3.{Colors.ENDC} Place a Bid")
        print(f"{Colors.CYAN}4.{Colors.ENDC} View Notifications")
        print(f"{Colors.CYAN}5.{Colors.ENDC} Exit")
        print(f"\n{Colors.BLUE}{'-' * 50}{Colors.ENDC}")

    def connect(self, name):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            self.socket.send(name.encode())
            
            response = self.socket.recv(1024).decode().strip()
            if response == "NAME_TAKEN":
                print(f"{Colors.RED}Error: This name is already taken. Please choose another name.{Colors.ENDC}")
                self.socket.close()
                return False
            
            self.name = name
            self.connected = True
            
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Connection error: {e}{Colors.ENDC}")
            return False

    def get_products_list(self):
        if not self.connected:
            print(f"{Colors.RED}Not connected to server{Colors.ENDC}")
            return
        
        try:
            command = {
                'type': 'GET_PRODUCTS_LIST'
            }
            self.socket.send(json.dumps(command).encode())
            time.sleep(0.1)
        except Exception as e:
            print(f"{Colors.RED}Error getting products list: {e}{Colors.ENDC}")

    def listen_for_messages(self):
        while self.connected:
            try:
                message = self.socket.recv(1024).decode().strip()
                if not message:
                    print(f"{Colors.RED}Received empty message{Colors.ENDC}")
                    break
                
                with self.message_lock:
                    self.message_queue.append(message)
                    self.handle_message(message)
            except Exception:
                break
        
        self.connected = False
        print(f"\n{Colors.RED}Disconnected from server{Colors.ENDC}")

    def handle_message(self, message):
        try:
            data = json.loads(message)
            if data['type'] == 'PRODUCTS_LIST':
                self.display_products(data['products'])
            else:
                print(f"\n{message}")
        except json.JSONDecodeError:
            if message.startswith("[Notification]"):
                print(f"\n{Colors.YELLOW}{message}{Colors.ENDC}")
            elif message == "PRODUCT_EXISTS":
                print(f"\n{Colors.RED}Product already exists{Colors.ENDC}")
            elif message == "BID_TOO_LOW":
                print(f"\n{Colors.RED}Bid is too low{Colors.ENDC}")
            elif message == "PRODUCT_NOT_FOUND":
                print(f"\n{Colors.RED}Product not found{Colors.ENDC}")
            elif message == "AUCTION_ENDED":
                print(f"\n{Colors.RED}This auction has already ended{Colors.ENDC}")
            else:
                print(f"\n{message}")

    def add_product(self, product_name, min_price):
        if not self.connected:
            print(f"{Colors.RED}Not connected to server{Colors.ENDC}")
            return
        
        try:
            command = {
                'type': 'ADD_PRODUCT',
                'product_name': product_name,
                'min_price': float(min_price)
            }
            self.socket.send(json.dumps(command).encode())
            time.sleep(0.1)
        except Exception as e:
            print(f"{Colors.RED}Error adding product: {e}{Colors.ENDC}")

    def place_bid(self, product_name, amount):
        if not self.connected:
            print(f"{Colors.RED}Not connected to server{Colors.ENDC}")
            return
        
        try:
            command = {
                'type': 'BID',
                'product_name': product_name,
                'amount': float(amount)
            }
            self.socket.send(json.dumps(command).encode())
            time.sleep(0.1)
        except Exception as e:
            print(f"{Colors.RED}Error placing bid: {e}{Colors.ENDC}")

    def display_products(self, products):
        print(f"\n{Colors.BOLD}Current Products:{Colors.ENDC}")
        print(f"{Colors.BLUE}{'-' * 50}{Colors.ENDC}")
        if not products:
            print(f"{Colors.YELLOW}No products available{Colors.ENDC}\n")
        else:
            for product in products:
                print(f"{Colors.GREEN}Product: {product['name']}{Colors.ENDC}")
                print(f"Owner: {product['owner']}")
                print(f"Current Price: {product['current_price']}")
                print(f"Starting Price: {product['min_price']}")
                print(f"{Colors.BLUE}{'-' * 50}{Colors.ENDC}")

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.socket.close()

def main():
    client = AuctionClient()
    client.clear_screen()
    client.print_header()
    
    while True:
        name = input(f"{Colors.CYAN}Enter your name: {Colors.ENDC}").strip()
        if name:
            if client.connect(name):
                break
    
    time.sleep(0.2)
    print(f"{Colors.GREEN}Connected as {name}{Colors.ENDC}")
    
    while client.connected:
        try:
            client.print_menu()
            choice = input(f"{Colors.CYAN}Select an option (1-5): {Colors.ENDC}").strip()
            
            if choice == "1":
                client.get_products_list()
            elif choice == "2":
                product_name = input(f"{Colors.CYAN}Enter product name: {Colors.ENDC}").strip()
                min_price = input(f"{Colors.CYAN}Enter minimum price: {Colors.ENDC}").strip()
                client.add_product(product_name, min_price)
            elif choice == "3":
                product_name = input(f"{Colors.CYAN}Enter product name: {Colors.ENDC}").strip()
                amount = input(f"{Colors.CYAN}Enter bid amount: {Colors.ENDC}").strip()
                client.place_bid(product_name, amount)
            elif choice == "4":
                print(f"\n{Colors.YELLOW}Recent notifications:{Colors.ENDC}")
                with client.message_lock:
                    for msg in client.message_queue[-5:]:
                        if msg.startswith("[Notification]"):
                            print(f"{Colors.YELLOW}{msg}{Colors.ENDC}")
            elif choice == "5":
                break
            else:
                print(f"{Colors.RED}Invalid option. Please select 1-5.{Colors.ENDC}")
            
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
            client.clear_screen()
            client.print_header()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
    
    client.disconnect()

if __name__ == "__main__":
    main()
