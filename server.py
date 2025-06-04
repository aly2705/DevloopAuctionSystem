import socket
import threading
import json
import time
from datetime import datetime, timedelta

class AuctionServer:
    def __init__(self, host='localhost', port=5000, auction_duration=300):  # 5 minute - durata default
        self.host = host
        self.port = port
        self.auction_duration = auction_duration
        self.clients = {}  # Structura client: {client_name: client_socket}
        self.products = {}  # Structura produs: {product_name: {'owner': owner_name, 'min_price': price, 'current_price': price, 'bidders': set(), 'end_time': datetime}}
        self.lock = threading.Lock()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")

        monitor_thread = threading.Thread(target=self.monitor_auctions)
        monitor_thread.daemon = True
        monitor_thread.start()

        while True:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()

    def handle_client(self, client_socket):
        try:
            client_name = client_socket.recv(1024).decode().strip()
            
            with self.lock:
                if client_name in self.clients:
                    client_socket.send("NAME_TAKEN".encode())
                    client_socket.close()
                    return
                
                self.clients[client_name] = client_socket
                client_socket.send("CONNECTED".encode())
                self.send_products_list(client_name)
                
                self.broadcast(f"[Notification] Client {client_name} has joined the auction", exclude=client_name)

            while True:
                message = client_socket.recv(1024).decode().strip()
                if not message:
                    break

                print(f"Received message: {message}")
                command = json.loads(message)
                print(f"Parsed command: {command}")
                self.handle_command(client_name, command)

        except Exception as e:
            print(f"Error handling client {client_name}: {e}")
            self.remove_client(client_name)
            

    def handle_command(self, client_name, command):
        print(f"Received command: {command}")
        cmd_type = command.get('type')
        
        if cmd_type == 'ADD_PRODUCT':
            product_name = command['product_name']
            min_price = command['min_price']
            
            with self.lock:
                if product_name in self.products:
                    self.send_to_client(client_name, "PRODUCT_EXISTS")
                    return
                
                self.products[product_name] = {
                    'owner': client_name,
                    'min_price': min_price,
                    'current_price': min_price,
                    'bidders': set(),
                    'end_time': datetime.now() + timedelta(seconds=self.auction_duration)
                }
                
                self.broadcast(f"[Notification] New product available: {product_name} from {client_name} starting at {min_price}")

        elif cmd_type == 'BID':
            product_name = command['product_name']
            bid_amount = command['amount']
            
            with self.lock:
                if product_name not in self.products:
                    self.send_to_client(client_name, "PRODUCT_NOT_FOUND")
                    return
                
                product = self.products[product_name]
                if datetime.now() > product['end_time']:
                    self.send_to_client(client_name, "AUCTION_ENDED")
                    return
                
                if bid_amount <= product['current_price']:
                    self.send_to_client(client_name, "BID_TOO_LOW")
                    return
                
                product['current_price'] = bid_amount
                product['bidders'].add(client_name)
                
                self.send_to_client(product['owner'], f"[Notification] New bid on {product_name}: {bid_amount} by {client_name}")
                for bidder in product['bidders']:
                    if bidder != client_name:
                        self.send_to_client(bidder, f"[Notification] New bid on {product_name}: {bid_amount} by {client_name}")

        elif cmd_type == 'GET_PRODUCTS_LIST':
            self.send_products_list(client_name)

    def monitor_auctions(self):
        while True:
            current_time = datetime.now()
            ended_auctions = []
            
            with self.lock:
                for product_name, product in self.products.items():
                    if current_time > product['end_time']:
                        ended_auctions.append((product_name, product))
                
                for product_name, product in ended_auctions:
                    del self.products[product_name]
                    self.broadcast(f"[Notification] Auction ended for {product_name}. Final price: {product['current_price']}")

            time.sleep(1)

    def send_products_list(self, client_name=None):
        products_info = []
        for name, product in self.products.items():
            if datetime.now() <= product['end_time']:
                products_info.append({
                    'name': name,
                    'owner': product['owner'],
                    'min_price': product['min_price'],
                    'current_price': product['current_price']
                })
        
        message = json.dumps({
            'type': 'PRODUCTS_LIST',
            'products': products_info
        })
        
        if client_name:
            self.send_to_client(client_name, message)
        else:
            self.broadcast(message)

    def broadcast(self, message, exclude=None):
        for name, client in self.clients.items():
            if name != exclude:
                try:
                    client.send(message.encode())
                except:
                    pass

    def send_to_client(self, client_name, message):
        if client_name in self.clients:
            try:
                self.clients[client_name].send(message.encode())
                print(f"Sent message to client {client_name}: {message}")  
            except Exception as e:
                print(f"Error sending to client {client_name}: {e}") 

    def remove_client(self, client_name):
        with self.lock:
            if client_name in self.clients:
                del self.clients[client_name]
                self.broadcast(f"[Notification] Client {client_name} has left the auction")

if __name__ == "__main__":
    server = AuctionServer()
    server.start()
