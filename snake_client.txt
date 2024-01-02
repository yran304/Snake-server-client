import re
import pygame
import socket
import threading
import sys
from snake import *
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Initialize game on client side
pygame.init()

# game board info
width = 500
rows = 20  # same width and rows like in snake.py
size_between = width // rows

server = "localhost"
port = 5555

# Generate CLIENT RSA key pair
##private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
##public_key = private_key.public_key()

# Serialize client public key to send to server
##public_key_bytes = public_key.public_bytes(
##    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)

# Connect to server using TCP since server is TCP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server, port))

# After Connection, send client's public key to server
##client_socket.send(public_key_bytes)

# And receive server's public key
##server_public_key_pem = client_socket.recv(1024)
##server_public_key = serialization.load_pem_public_key(server_public_key_pem, backend=default_backend())

# Set up the game display
window = pygame.display.set_mode((width, width))
pygame.display.set_caption("Snake Game")


# draw_grid function draws lines on the board to visualize the board
def draw_grid(width, rows, surface):
    size_between = width // rows
    x, y = 0, 0
    for line in range(rows):
        x = x + size_between
        y = y + size_between

        pygame.draw.line(surface, (255, 255, 255), (x, 0), (x, width))
        pygame.draw.line(surface, (255, 255, 255), (0, y), (width, y))


def redraw_window(surface, snakes_info, snacks_info):
    global rows, width
    surface.fill((0, 0, 0))  # fills the surface with one single color when redraw (to reset)
    draw_grid(width, rows, surface)

    # Create each snake object and draw it
    for snake_info in snakes_info:
        if snake_info:  # Ensure there is at least one segment of the snake
            # Create current snake object
            head_pos = snake_info[0]
            snake_color = (255, 0, 0) if snakes_info.index(snake_info) == 0 else (0, 0, 255)  # Different color for each snake
            snake_obj = snake(snake_color, head_pos)
            snake_obj.body = [cube(pos, color=snake_color) for pos in snake_info]
            snake_obj.draw(surface)

    # Draw the snacks
    for snack_pos in snacks_info:
        snack_cube = cube(snack_pos, color=(0, 255, 0))  # Assuming snacks are green
        snack_cube.draw(surface)

    pygame.display.update()


def listen_server(socket):
    while True:
        try:
            # Get game state from server
            data = socket.recv(1024).decode()
            if not data:
                print("Disconnect")
                break
            if data.startswith('msg:'):  # it is a message not game state
                # Handling chat message
                chat_message = data[4:]
                print(f"{chat_message}")
            else:  # Parse the game state received from server
                parse_state = parse_game_state(data)
                if len(parse_state) == 2:
                    snakes, snacks = parse_game_state(data)
                    redraw_window(window, snakes, snacks)
        except Exception as e:
            print("Player removed, Disconnected")
            break


# send command info to server
def send_command(command):
    try:
        client_socket.send(command.encode())
    except Exception as e:
        print("Error. Fail to send command to server.", e)


def parse_game_state(state):
    # parse the state information sent by server
    snake_data, snack_data = state.split("|")

    def parse_snake_coordinates(data):
        snakes = []
        # Split the data by '**' to separate different snakes
        for snake_str in data.split("**"):
            coordinates = []
            # Split again with '*' to separate positions for each snake
            for pos_str in snake_str.split("*"):
                if pos_str:
                    # Remove parentheses
                    pos_str = pos_str.replace('(', '').replace(')', '')
                    # Convert the string elements to integers and append as a tuple
                    try:
                        x, y = map(int, pos_str.split(','))
                        coordinates.append((x, y))
                    except ValueError as e:
                        print(f"Error parsing snake position {pos_str}: {e}")
            snakes.append(coordinates)
        return snakes

    # Function to parse snack coordinates, which are separated by '**'
    def parse_snack_coordinates(data):
        coordinates = []
        # Split the data by '**' to separate positions for the snacks
        for pos_str in data.split("**"):
            if pos_str:
                # Remove parentheses
                pos_str = pos_str.replace('(', '').replace(')', '')
                # Convert the string elements to integers and append as a tuple
                try:
                    x, y = map(int, pos_str.split(','))
                    coordinates.append((x, y))
                except ValueError as e:
                    print(f"Error parsing snack position {pos_str}: {e}")
        return coordinates

    # Parse the coordinates for the snake and snacks
    snakes = parse_snake_coordinates(snake_data)
    snacks = parse_snack_coordinates(snack_data)

    return snakes, snacks


def main():
    threading.Thread(target=listen_server, args=(client_socket,), daemon=True).start()

    running = True
    while running:
        try:
            send_command("get")
            pygame.time.delay(100)  # Delay 100 millisecs
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    send_command("quit")
                    running = False
                    break  # break immediately to avoid sending after disconnect

            if not running:  # Check if we are still running before processing keys
                continue

            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                send_command("up")
            elif keys[pygame.K_DOWN]:
                send_command("down")
            elif keys[pygame.K_LEFT]:
                send_command("left")
            elif keys[pygame.K_RIGHT]:
                send_command("right")
            elif keys[pygame.K_r]:
                send_command("reset")
            elif keys[pygame.K_q]:
                send_command("quit")
                running = False
            elif keys[pygame.K_z]:
                send_command("Congratulations!")
            elif keys[pygame.K_x]:
                send_command("It works!")
            elif keys[pygame.K_c]:
                send_command("Ready?")

        except KeyboardInterrupt:
            send_command("quit")
            running = False

    client_socket.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
