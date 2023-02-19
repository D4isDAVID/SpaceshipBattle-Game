import math
import pygame
import os
import sys
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from background import Background
from entity.player import PlayerEntity
from entity.bullet import BulletEntity
pygame.init()
VERSION = '0.4.5-alpha'


class Lobby:
    FONT = pygame.font.SysFont('Arial', 25)
    BIG_FONT = pygame.font.SysFont('Arial', 50)
    TARGET_FPS = 144

    def __init__(self):
        self.resolution = [1280, 720]
        self.window = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.surface = pygame.Surface((1280, 720))
        self.minimap = pygame.Surface((3500, 3500))
        self.background = Background(1250, 1250, (0.1, -0.1))
        self.id = None
        self.entities = {}
        self.entity_id = None
        self.move = [False, False, False, False, False]
        self.assets = {}
        path = os.path.dirname(os.path.realpath( __file__ ))
        self.assets['rocket_red'] = pygame.image.load(os.path.join(path, 'assets', 'rocket_red.png'))
        self.assets['rocket2_red'] = pygame.image.load(os.path.join(path, 'assets', 'rocket2_red.png'))
        self.assets['alien_red'] = pygame.image.load(os.path.join(path, 'assets', 'alien_red.png'))
        self.assets['alien2_red'] = pygame.image.load(os.path.join(path, 'assets', 'alien2_red.png'))
        self.assets['rocket_blue'] = pygame.image.load(os.path.join(path, 'assets', 'rocket_blue.png'))
        self.assets['theme'] = os.path.join(path, 'assets', 'theme.mp3')
        self.enemy_assets = {0: 'rocket_red', 1: 'rocket2_red', 2: 'alien_red', 3: 'alien2_red'}
        self.client = socket(AF_INET, SOCK_STREAM)

    def draw(self, delta_time):
        self.surface.fill(0)
        self.minimap.fill(0)
        e = self.entities.get(self.entity_id, PlayerEntity(1500, 1500, 270, 0, 0, 0, 0, '', self.assets['rocket_blue'], (0, 0, 255)))
        self.background.update(delta_time, self.TARGET_FPS)
        self.background.draw(self.surface, e)
        width, height = self.surface.get_size()
        border_size = 10
        border_x = border_size - e.x + width/2
        border_y = border_size - e.y + height/2
        border_rect = (border_x, border_y, 3500-border_size*2, 3500-border_size*2)
        pygame.draw.rect(self.surface, (255, 0, 0), border_rect, border_size)
        minimap_size = 200
        pygame.draw.rect(self.minimap, (255, 255, 255), (0, 0, 3485, 3485), 30)
        count = 0
        for entity_id in list(self.entities.keys()):
            if entity_id in self.entities:
                entity = self.entities[entity_id]
                if isinstance(entity, PlayerEntity):
                    count += 1
                    entity.draw_score(self.surface, count)
                    if entity.hp > 0:
                        if entity_id == self.entity_id:
                            e = entity
                            e.move = self.move
                        entity.draw(self.surface, self.minimap, e)
                    else:
                        if entity_id == self.entity_id:
                            text = self.BIG_FONT.render('YOU ARE DEAD', True, (255, 0, 0))
                            text2 = self.FONT.render('Get ready to spawn...', True, (255, 255, 255))
                            self.surface.blit(text, (640 - text.get_width() // 2, 240))
                            self.surface.blit(text2, (640 - text2.get_width() // 2, 240 + text.get_height()))
                else:
                    entity.draw(self.surface, e, self.entity_id)
                entity.update(delta_time, self.TARGET_FPS)
        text = self.FONT.render(f'({int(e.x)}, {int(e.y)})', True, (255, 255, 255))
        self.surface.blit(text, (10, 675))
        self.minimap.set_alpha(200)
        self.surface.blit(pygame.transform.scale(self.minimap, (minimap_size, minimap_size)), (15, 15))

    def deserialize(self, data_full, remains):
        deserialized = {}
        data_list = data_full.split('||')
        if not isinstance(data_list, list): data_list = [data_list]
        if len(data_list) > 2:
            data = data_list[-2]
        else:
            data = remains + data_list[0]
        if (len(data_list) > 2) or (len(data_list) > 1 and not data_list[-1]):
            entities = data.split('|')
            for e in entities:
                i = e.split('-', 1)
                entity_id = int(i[0])
                entity = i[1]
                if entity.count(',') > 4:
                    values = entity.split(',', 11)
                    move = (values[6], values[7], values[8], values[9], values[10])
                    move = tuple(bool(int(i)) for i in move)
                    if entity_id == self.entity_id:
                        asset = self.assets['rocket_blue']
                        color = (0, 0, 255)
                    else:
                        asset = self.assets[self.enemy_assets[entity_id%4]]
                        color = (255, 0, 0)
                    deserialized[entity_id] = PlayerEntity(
                        float(values[0]),
                        float(values[1]),
                        float(values[2]),
                        int(values[3]),
                        int(values[4]),
                        float(values[5]),
                        move,
                        values[11],
                        asset,
                        color
                    )
                else:
                    values = entity.split(',')
                    deserialized[entity_id] = BulletEntity(
                        float(values[0]),
                        float(values[1]),
                        int(values[2]),
                        (float(values[3]), float(values[4]))
                    )

            self.entities = deserialized
        return data_list[-1]

    def get_thread(self):
        remains = ''
        while 1:
            try:
                reply = self.client.recv(8196)
                remains = self.deserialize(reply.decode(), remains)
            except ValueError:
                continue
            except Exception as e:
                print(f'Exception | {e}')
                break

    def main(self, name, hostname, port=7723):
        try:
            clock = pygame.time.Clock()
            self.client.connect((hostname, port))
            self.id = self.client.recv(1024).decode()
            self.client.sendall(f'join-{name}'.encode())
            self.entity_id = int(self.client.recv(1024).decode().split('|')[0])
            thread = Thread(target=self.get_thread)
            thread.daemon = True
            thread.start()
            pygame.mixer.music.load(self.assets['theme'])
            volume = 0.5
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=-1)
            version_text = self.FONT.render(VERSION, True, (255, 255, 255))
            running = 1

            while running:
                fps = 60 if pygame.key.get_focused() or pygame.mouse.get_focused() else 15
                delta_time = clock.tick(fps) / 1000
                self.draw(delta_time)
                self.surface.blit(version_text, (1270-version_text.get_width(), 675))
                fps_text = self.FONT.render(f'{int(clock.get_fps())} FPS', True, (255, 255, 255))
                self.surface.blit(fps_text, (1270-fps_text.get_width(), 650))
                surface = pygame.transform.scale(self.surface, self.resolution)
                res = pygame.display.get_window_size()
                self.window.blit(surface, (res[0]/2-surface.get_width()/2, res[1]/2-surface.get_height()/2))
                pygame.display.update()

                events = {}
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        running = 0
                        break
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_w: self.move[0] = True
                        elif event.key == pygame.K_a: self.move[1] = True
                        elif event.key == pygame.K_s: self.move[2] = True
                        elif event.key == pygame.K_d: self.move[3] = True
                        elif event.key == pygame.K_LSHIFT: self.move[4] = True
                        events['move'] = self.move
                    elif event.type == pygame.KEYUP:
                        if event.key == pygame.K_w:self.move[0] = False
                        elif event.key == pygame.K_a: self.move[1] = False
                        elif event.key == pygame.K_s: self.move[2] = False
                        elif event.key == pygame.K_d: self.move[3] = False
                        elif event.key == pygame.K_LSHIFT: self.move[4] = False
                        elif event.key == pygame.K_m:
                            if pygame.mixer.music.get_volume() == 0:
                                pygame.mixer.music.set_volume(volume)
                            else:
                                pygame.mixer.music.set_volume(0)
                        elif event.key == pygame.K_EQUALS:
                            volume += 0.05
                            if volume > 1: volume = 1
                            pygame.mixer.music.set_volume(volume)
                        elif event.key == pygame.K_MINUS:
                            volume -= 0.05
                            if volume < 0: volume = 0
                            pygame.mixer.music.set_volume(volume)
                        events['move'] = self.move
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        width, height = pygame.display.get_window_size()
                        pos = [pos[0]-width/2, pos[1]-height/2]
                        events['shoot'] = math.atan2(pos[1], pos[0]) / math.pi * 180
                    elif event.type == pygame.VIDEORESIZE:
                        self.resolution[1] = event.h
                        self.resolution[0] = round(event.h / 0.5625)

                serialized = ''
                for event, value in events.items():
                    serialized += f'{event}-'
                    if event == 'move':
                        for i in value:
                            serialized += f'{int(i)},'
                        serialized = serialized[:-1]
                    elif event == 'shoot':
                        serialized += str(value)
                    serialized += '|'

                if serialized: self.client.sendall(serialized.encode())
        except OSError as e:
            if e.errno == 11001 or e.errno == 10049:
                print('Exception | Invalid IP')
            elif e.errno == 10054:
                print('Exception | Server Closed')
            elif e.errno == 10061:
                print("Exception | Couldn't connect to server")
            else:
                print(f'Exception | {e}')


if __name__ == '__main__':
    try:
        ip, *port = input('Enter Server IP (ip or ip:port): ').split(':')
        if len(port) == 0:
            port = 7723
        else:
            try:
                port = int(port[0])
            except ValueError:
                print('Invalid Port')
                sys.exit()
        print(f'Using the IP {ip}:{port}')
        name = input('Enter Desired Name: ')
        lobby = Lobby()
        lobby.main(name, ip, port)
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
