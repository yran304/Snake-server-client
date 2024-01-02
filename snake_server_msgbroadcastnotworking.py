import numpy as np
import socket
from _thread import *
from snake import SnakeGame
import uuid
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# Generate RSA Key Pair for the SERVER
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
public_key = private_key.public_key()
# Serialize Public Key to send to the client
public_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
# server = "10.11.250.207"
server = "localhost"
port = 5555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

counter = 0
rows = 20

try:
    s.bind((server, port))
except socket.error as e:
    print(str(e))

s.listen()  # Listen without limiting the number of connections since could have multiple clients connecting
print("Server Started, waiting for a connection...")

clients = {}  # Dictionary to store client connection info
clients_public_key = {}  # Dictionary to store each client's public key

# Game setup
game = SnakeGame(rows)
game_state = ""
last_move_timestamp = time.time()
interval = 0.2
moves_queue = set()


def game_thread():
    global game, moves_queue, game_state
    while True:
        last_move_timestamp = time.time()
        game.move(moves_queue)
        moves_queue = set()
        game_state = game.get_state()
        while time.time() - last_move_timestamp < interval:
            time.sleep(0.1)


rgb_colors = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}
rgb_colors_list = list(rgb_colors.values())


def client_thread(conn, player_id):
    global game, moves_queue

    while True:
        try:
            # All data sent from client to server will be encrypted
            encrypted_data = conn.recv(1024)
            if not encrypted_data:
                break
            # Decrypt using server's private key
            data = private_key.decrypt(
                encrypted_data,
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                             algorithm=hashes.SHA256(),
                             label=None)
            ).decode()
            if data == "get":
                conn.send(game.get_state().encode())
            elif data in ["up", "down", "left", "right"]:
                moves_queue.add((player_id, data))
            elif data == "reset":
                game.reset_player(player_id)
            elif data in ["Congratulations!", "It works!", "Ready?"]:
                broadcast_message(data)
            elif data == "quit":
                game.remove_player(player_id)
                conn.close()
                del clients[player_id]
                del clients_public_key[player_id]
                break
        except OSError as e:
            print(f"{e}")
            game.remove_player(player_id)
            conn.close()
            del clients[player_id]
            del clients_public_key[player_id]
            break
        except Exception as e:
            print(f"Error with client {player_id}: {e}")
            continue


def broadcast_message(message):
    # print('XXX', message.encode())
    for player_id, conn in clients.items():
        client_public_key = clients_public_key[player_id]
        # Encrypt only the message
        encrypted_msg = client_public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        formatted_message = f"msg:{player_id}:{encrypted_msg}"
        conn.send(formatted_message.encode())


def main():
    global counter, game, clients

    while True:  # Loop to accept multiple clients
        conn, addr = s.accept()
        print("Connected to:", addr)

        unique_id = str(uuid.uuid4())

        # Upon connection, send server's public key to the client
        conn.send(public_key_bytes)

        # Store client connection
        clients[unique_id] = conn

        # Receive and store client's public key
        client_public_key_pem = conn.recv(1024)
        client_public_key = load_pem_public_key(client_public_key_pem, backend=default_backend())
        clients_public_key[unique_id] = client_public_key

        color = rgb_colors_list[np.random.randint(0, len(rgb_colors_list))]
        game.add_player(unique_id, color=color)

        start_new_thread(game_thread, ())

        # Handle client in a separate thread
        start_new_thread(client_thread, (conn, unique_id))


if __name__ == "__main__":
    main()
