import pygame
import sys
import numpy as np
import requests
import os
import json
import hashlib


file_data_list = []

with open(f"data/%3flevel=0", "rb") as filehandle:
    file_data_list.append(filehandle.read())
with open(f"data/%3flevel=1_base16", "rb") as filehandle:
    file_data_list.append(filehandle.read())
with open(f"data/%3flevel=2", "rb") as filehandle:
    file_data_list.append(filehandle.read())
with open(f"data/%3flevel=3_rc4", "rb") as filehandle:
    file_data_list.append(filehandle.read())
with open(f"data/%3flevel=4_aes", "rb") as filehandle:
    file_data_list.append(filehandle.read())


decryptor = ""
hs = ""
nr_maps = 5
pw_file = "pwstore.txt"
payload = file_data_list


COLORS_RGB = {'Black': (0, 0, 0),
              'White': (255, 255, 255),
              'dim grey': (105, 105, 105),
              'dim grey': (105, 105, 105),
              'orange red': (255, 69, 0),
              'Red': (255, 0, 0),
              'Green': (0, 255, 0),
              'slate gray': (112, 128, 144),
              }


workdir = os.path.dirname(os.path.abspath(__file__))
graphics_dir = os.path.join(workdir, 'graphics')


def clear_graphics(target):
    for f in os.listdir(target):
        p = os.path.join(target, f)
        if 'ball' in p or '640px' in p:
            os.remove(p)


SERVER_URL = 'http://127.0.0.5:8000'
SERVER_URL = 'http://192.168.121.129:8000'

SIZE_X = 1200
SIZE_Y = 700
DRAW_AREA = [0, SIZE_X, 0, SIZE_Y]
MIN_R = 12
MAX_VY = 4
height_ground = 40
fps = 60


class Player:
    def __init__(self, fn, fn_hit, parent, x, y_ground, vel, min_x, max_x, extra_lives):
        self.parent = parent

        self.x = x
        self.y_ground = y_ground
        self.vel = vel

        # Standard player
        self.fn = fn
        self.img0 = pygame.image.load(fn)
        self.img0.convert()
        x0, y0, w, h = self.img0.get_rect()
        self.img = pygame.transform.scale(self.img0, (30, 55))
        x0, y0, self.w, self.h = self.img.get_rect()

        # Player who got hit by ball
        self.fn_hit = fn_hit
        self.img0_hit = pygame.image.load(fn_hit)
        self.img0_hit.convert()
        x0, y0, w, h = self.img0_hit.get_rect()
        self.img_hit = pygame.transform.scale(self.img0_hit, (30, 55))
        x0, y0, self.w_hit, self.h_hit = self.img_hit.get_rect()

        self.min_x = min_x
        self.max_x = max_x - self.w

        # Upper left corner
        self.y = SIZE_Y - self.y_ground - self.h

        self.parent.blit(self.img, (self.x, self.y))

        self.projectiles = []
        self.reloading = 0

        self.extra_lives = extra_lives
        self.got_hit_cooldown = 0
        self.points = 0

    def move(self, keys_pressed):
        if keys_pressed[pygame.K_LEFT] and self.x > (self.min_x):
            self.x -= self.vel
        if keys_pressed[pygame.K_RIGHT] and self.x < (self.max_x):
            self.x += self.vel

        if self.got_hit_cooldown > 0:
            self.parent.blit(self.img_hit, (self.x, self.y))
        else:
            self.parent.blit(self.img, (self.x, self.y))

        fired = False
        if keys_pressed[pygame.K_SPACE]:
            fired = True

        if fired and self.reloading == 0:
            speed = 5
            length = 30
            p = Projectile(self, COLORS_RGB['orange red'], speed, length)
            self.projectiles.append(p)
            self.reloading = 30

        if self.reloading > 0:
            self.reloading -= 1

        dead = []
        for p in self.projectiles:
            if not p.reached_top:
                p.move()
            else:
                dead.append(p)
        self.projectiles = list(set(self.projectiles) - set(dead))

    def check_projectile_hits(self, balls):
        dead = []
        new_balls = []
        used_projectiles = []

        for p in self.projectiles:
            for b in balls:
                x1 = x2 = p.x
                y_low, y_high = p.y0, p.y0 - p.length
                if b.is_hit(x1, y_low, y_high):
                    # if b.r > MIN_R:
                    if b.nr_hits != 1:  # its reduced to 0 at split, i.e. 1 here = "dead"
                        b1, b2 = b.split()
                        new_balls.append(b1)
                        new_balls.append(b2)
                        self.points += 1
                    else:
                        pass
                    dead.append(b)
                    used_projectiles.append(p)
                    break
        self.projectiles = list(set(self.projectiles) - set(used_projectiles))
        balls2 = list(set(balls) - set(dead))
        balls2 = balls2 + new_balls
        return balls2

    def check_ball_collision(self, balls):
        for b in balls:

            x_left = self.x
            x_right = self.x + self.w
            ball_center_x = b.x + b.r
            ball_center_y = b.y + b.r
            dist_upper_left = np.sqrt(
                (ball_center_x - x_left)**2 + (ball_center_y - self.y)**2)
            dist_upper_right = np.sqrt(
                (ball_center_x - x_right)**2 + (ball_center_y - self.y)**2)
            if self.got_hit_cooldown == 0 and (dist_upper_left < b.r or dist_upper_right < b.r):
                self.extra_lives -= 1
                self.got_hit_cooldown = 120

            if self.got_hit_cooldown > 0:
                self.got_hit_cooldown -= 1


class Projectile:
    def __init__(self, player, color, v, length, width=5, fn=None):
        self.player = player
        self.parent = player.parent
        self.color = color

        self.x = int(player.x + player.w / 2.)
        self.y0 = player.y  # top of player
        self.v = v
        self.width = width  # width of shot (the line)
        self.length = length  # length of shot (the line)

        self.reached_top = False

    def move(self):
        self.y0 -= self.v
        bottom_pos = [self.x, self.y0]  # bottom pos
        top_pos = [self.x, self.y0 - self.length]  # top pos

        pygame.draw.line(self.parent, self.color,
                         bottom_pos, top_pos, self.width)

        if bottom_pos[1] < 0:
            self.reached_top = True


class Ball:
    def __init__(self, parent, fn, x, vx, y, vy, nr_hits, allowed_area,
                 g=-0.1, impact_loss=0.8):
        self.parent = parent

        self.allowed_area = allowed_area
        self.x = x
        self.vx = vx
        self.y = y
        self.vy = vy
        self.r = MIN_R * nr_hits
        self.nr_hits = nr_hits
        self.fn = fn

        self.img0 = pygame.image.load(fn)
        self.img0.convert()
        x0, y0, w, h = self.img0.get_rect()
        self.img_scale = 2 * self.r / w
        self.angle = 0
        self.img = pygame.transform.rotozoom(
            self.img0, self.angle, self.img_scale)

        self.g = -0.1
        self.impact_loss = 0.8

    def split(self):
        ball1 = Ball(self.parent, self.fn, self.x, 1*self.vx,
                     self.y, -1.2*abs(self.vy), self.nr_hits-1, self.allowed_area)

        ball2 = Ball(self.parent, self.fn, self.x, -1*self.vx,
                     self.y, -1.2*abs(self.vy), self.nr_hits-1, self.allowed_area)
        return ball1, ball2

    def hit_wall(self, walls):
        x_center = self.x + self.r
        for w in walls:
            if w.x < x_center:  # ball to the right of wall
                x_wall = w.x + int(w.width / 2.)  # add half width
            else:  # ball to the right of wall
                x_wall = w.x - int(w.width / 2.)  # subtract half width
            if abs(x_wall-x_center) < self.r:
                return True
        return False

    def move(self, walls):
        min_x, max_x, min_y, max_y = self.allowed_area

        # Rectangle ball: x,y upper left
        self.x += self.vx
        if (self.x > (max_x-2*self.r)) or (self.x < (min_x)) or self.hit_wall(walls):
            self.vx *= -1

        self.y += self.vy
        self.vy -= self.g

        if self.y > (max_y-2*self.r):
            self.vy *= -1 * self.impact_loss

        self.x = int(self.x)
        self.y = int(self.y)
        self.parent.blit(self.img, (self.x, self.y))

    def is_hit(self, x, y_low, y_high):
        center_x = self.x + self.r
        center_y = self.y + self.r
        dist_low = np.sqrt((center_x - x)**2 + (center_y - y_low)**2)
        dist_high = np.sqrt((center_x - x)**2 + (center_y - y_high)**2)
        if dist_low <= self.r or dist_high <= self.r:
            return True
        return False


class Wall:
    def __init__(self, parent, x, y_min, y_max, width, width_edge=5):
        self.parent = parent
        self.x = int(x - width / 2.)
        self.width = width
        self.y_min = y_min
        self.y_max = y_max
        self.color = COLORS_RGB['slate gray']
        self.bottom_pos = (self.x, self.y_min)
        self.top_pos = (self.x, self.y_max)

        self.width_edge = width_edge
        self.edge_left_min = (int(self.x-self.width/2.), self.y_min)
        self.edge_left_max = (int(self.x-self.width/2.), self.y_max)
        self.edge_right_min = (int(self.x+self.width/2.), self.y_min)
        self.edge_right_max = (int(self.x+self.width/2.), self.y_max)
        self.edge_bottom_left = (
            int(self.x-self.width/2.-self.width_edge/2.+1), self.y_max)
        self.edge_bottom_right = (
            int(self.x+self.width/2.+self.width_edge/2.), self.y_max)

    def draw(self):
        pygame.draw.line(self.parent, self.color,
                         self.bottom_pos, self.top_pos, self.width)
        pygame.draw.line(
            self.parent, COLORS_RGB['Black'], self.edge_left_min, self.edge_left_max, self.width_edge)
        pygame.draw.line(
            self.parent, COLORS_RGB['Black'], self.edge_right_min, self.edge_right_max, self.width_edge)
        pygame.draw.line(
            self.parent, COLORS_RGB['Black'], self.edge_bottom_left, self.edge_bottom_right, self.width_edge)


class Background:
    def __init__(self, fn, parent, allowed_area, height_ground, color_ground):
        self.parent = parent
        self.allowed_area = allowed_area
        self.height_ground = height_ground
        self.color_ground = color_ground

        self.fn = fn
        self.img0 = pygame.image.load(self.fn)
        self.img0.convert()
        x0, y0, w, h = self.img0.get_rect()

        self.img_scale_x = SIZE_X / w
        self.img_scale_y = SIZE_Y / w
        self.angle = 0
        self.img = pygame.transform.scale(self.img0, (SIZE_X, SIZE_Y))

        self.draw()

    def draw(self):
        min_x = self.allowed_area[0]
        min_y = self.allowed_area[3] - self.height_ground
        width = self.allowed_area[1]
        height = self.height_ground
        ground_rect = (min_x, min_y, width, height)

        self.parent.blit(self.img, (0, 0))

        pygame.draw.rect(self.parent, self.color_ground, ground_rect)


class Scoreboard:
    def __init__(self, parent):
        self.parent = parent
        self.myfont = pygame.font.SysFont('Comic Sans MS', 30, bold=True)
        self.text_color = COLORS_RGB['Black']
        self.bg_color = COLORS_RGB['White']

    def update(self, level, score, lives):
        aliasing = False
        score_text = self.myfont.render(f'Level {str(level)} Points {str(score).zfill(4)} Lives {lives}',
                                        aliasing, self.text_color, self.bg_color)
        self.parent.blit(score_text, (0, 0))


class FinishScreen:
    def __init__(self, parent):
        self.parent = parent
        self.myfont = pygame.font.SysFont('Comic Sans MS', 40, bold=True)
        self.time_left = 300

    def update_failed(self, score):
        text_color = COLORS_RGB['Black']
        bg_color = COLORS_RGB['Red']
        aliasing = False
        t0 = self.time_left / fps
        score_text = self.myfont.render(f'GAME OVER! Total points {str(score).zfill(4)}. Ending in {t0:.2f} s.',
                                        aliasing, text_color, bg_color)

        x, y, w, h = score_text.get_rect()
        x0 = int(SIZE_X / 2. - w / 2.)
        y0 = int(SIZE_Y / 2. - h / 2.)
        self.parent.blit(score_text, (x0, y0))

    def update_done(self, score):
        text_color = COLORS_RGB['Black']
        bg_color = COLORS_RGB['Green']
        aliasing = False
        t0 = self.time_left / fps
        score_text = self.myfont.render(f'ALL LEVELS COMPLETED! Total points {str(score).zfill(4)}. Ending in {t0:.2f} s.',
                                        aliasing, text_color, bg_color)

        x, y, w, h = score_text.get_rect()
        x0 = int(SIZE_X / 2. - w / 2.)
        y0 = int(SIZE_Y / 2. - h / 2.)
        self.parent.blit(score_text, (x0, y0))


# ############################################################3
# ############################################################3
# ############################################################3


def load_map_from_local(level):

    params_map = json.loads(payload[level])

    for ball in params_map['balls']:
        dat = ball['data']
        p = os.path.join(graphics_dir, ball['fn'])
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        ball.pop('data', None)
        ball['fn'] = p

    dat = params_map['background']['data']
    fn = params_map['background']['fn']
    p = os.path.join(graphics_dir, fn)
    with open(p, 'wb') as f:
        f.write(dat.encode('latin1'))
    params_map['background'].pop('data', None)
    params_map['background']['fn'] = p

    if True or level == 0:  # if 0, load player too
        fn = params_map['player']['fn']
        dat = params_map['player']['data']
        p = os.path.join(graphics_dir, fn)
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        params_map['player'].pop('data', None)
        params_map['player']['fn'] = p

        fn_hit = params_map['player']['fn_hit']
        p = os.path.join(graphics_dir, fn_hit)
        dat = params_map['player']['data_hit']
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        params_map['player'].pop('data_hit', None)
        params_map['player']['fn_hit'] = p

    return params_map


def load_map_from_server(level):
    # Check if more levels are available,
    r = requests.get(SERVER_URL, params={'level': level}, headers=hs[level])

    if r.status_code == 204:  # no content, all levels are loaded
        return None

    if not r.status_code == 200:
        print('Error', r.status_code)
        sys.exit()

    params_map = r.content
    params_map = decryptor(level, params_map)
    params_map = json.loads(params_map)
    for ball in params_map['balls']:
        dat = ball['data']
        p = os.path.join(graphics_dir, ball['fn'])
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        ball.pop('data', None)
        ball['fn'] = p

    dat = params_map['background']['data']
    fn = params_map['background']['fn']
    p = os.path.join(graphics_dir, fn)
    with open(p, 'wb') as f:
        f.write(dat.encode('latin1'))
    params_map['background'].pop('data', None)
    params_map['background']['fn'] = p

    if True or level == 0:  # if 0, load player too
        fn = params_map['player']['fn']
        dat = params_map['player']['data']
        p = os.path.join(graphics_dir, fn)
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        params_map['player'].pop('data', None)
        params_map['player']['fn'] = p

        fn_hit = params_map['player']['fn_hit']
        p = os.path.join(graphics_dir, fn_hit)
        dat = params_map['player']['data_hit']
        with open(p, 'wb') as f:
            f.write(dat.encode('latin1'))
        params_map['player'].pop('data_hit', None)
        params_map['player']['fn_hit'] = p

    return params_map


def launch_new_level(params, player):
    player_area = DRAW_AREA.copy()
    min_x = player_area[0]
    max_x = player_area[1]
    x = params['player']['x']
    y_ground = height_ground
    vel = params['player']['vel']
    extra_lives = params['player']['extra_lives']
    fn = params['player']['fn']
    fn_hit = params['player']['fn_hit']
    if player is None:  # only init player the first time
        player = Player(fn, fn_hit, window, x, y_ground,
                        vel, min_x, max_x, extra_lives)
    else:
        player.x = params['player']['x']

    balls = []
    ball_area = DRAW_AREA.copy()
    ball_area[3] -= height_ground
    balls = []
    for b in params['balls']:
        b['allowed_area'] = ball_area
        ball = Ball(window, **b)
        balls.append(ball)

    walls = []
    for w in params['walls']:
        y_min = 0
        y_max = int(SIZE_Y-height_ground-1.2*player.h)
        wall = Wall(window, w['x'], y_min, y_max, w['width'])
        walls.append(wall)

    # background

    color_ground = COLORS_RGB['dim grey']
    fn = params['background']['fn']
    background = Background(fn, window, DRAW_AREA, height_ground, color_ground)

    return balls, walls, player, background


def is_offline():
    try:
        r = requests.head(SERVER_URL)  # Check if more levels are available,
        return False
    except Exception as e:
        return True


def load_map_and_params(offline, level):
    if offline:
        # Load maps from local folder
        # TODO
        # print("\n[!] Offline mode not implemented, exiting [!]\n")
        # sys.exit()
        return load_map_from_local(level)
    else:
        return load_map_from_server(level)


def store_new_keys(fn):
    if not os.path.exists(fn):
        key = input('Enter 6 random lower case letters to use as password: ')
        while len(key) != 6 or not key.islower():
            key = input(
                '\nPassword must be 6 lower case letters, try again!\nEnter 6 random lower case letters to use as password: ')
        pw = hashlib.md5(key.encode('latin1')).hexdigest()
        iv = pw[0:16]
        print(f'Storing password and IV to {fn=}')
        with open(fn, 'w') as f:
            f.write(f'{pw}\n{iv}')
        sys.exit()

# ############################################################3
# Init things
# ############################################################3


store_new_keys(pw_file)

# level=0 corresponds to an initiation, also loading the player
params_init = load_map_and_params(is_offline(), level=4)

pygame.init()
window = pygame.display.set_mode((SIZE_X, SIZE_Y))
pygame.display.set_caption("Bubbelproblem")
# you have to call this at the start, if you want to use this module.
pygame.font.init()


# scoreboard
scoreboard = Scoreboard(window)
finish_screen = FinishScreen(window)

balls, walls, player, background = launch_new_level(params_init, None)


# ##############################################################
# Game loop
# ##############################################################

if __name__ == '__main__':
    clock = pygame.time.Clock()

    level = 4
    finished = False
    run = True
    n = False
    while run:
        clock.tick(fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    n = True
        keys_pressed = pygame.key.get_pressed()

        background.draw()

        #  All lives are out, still showing finish screen
        if player.extra_lives == 0 and finish_screen.time_left > 0:
            finish_screen.time_left -= 1
            finish_screen.update_failed(player.points)
            pygame.display.update()
            continue

        #
        if (finished or len(balls) == 0) and finish_screen.time_left > 0:
            finish_screen.time_left -= 1
            finsihed = True
            finish_screen.update_done(player.points)
            pygame.display.update()
            continue

        # Finish screen timer is out, quit game
        if finish_screen.time_left <= 0:
            run = False
            continue

        # Nothing special, update game as usual
        for w in walls:
            w.draw()

        for b in balls:
            b.move(walls)

        player.move(keys_pressed)
        balls = player.check_projectile_hits(balls)
        player.check_ball_collision(balls)

        scoreboard.update(level+1, player.points, player.extra_lives)

        if (len(balls) == 0) or n:
            level += 1
            if level < nr_maps:
                params = load_map_and_params(is_offline(), level)
            else:
                params = None
            n = False

            if params is not None:
                balls, walls, player, background = launch_new_level(
                    params, player)
            else:
                finished = True

        pygame.display.update()

    pygame.quit()
