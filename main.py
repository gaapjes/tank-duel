import asyncio
from random import randint
import copy
import math
import sys
import string

import numpy as np
import pygame


# Global constants
###################################################################################

# World generator settings
MINSAMPLES = 5
ITERATIONS = 4

# Screen resolution
HRES = 1280
VRES = 720

# Game engine settings
TICKRATE = 60
GRAVITY = -10
INPUT_SCALE = 700 / HRES #0.5
TIME_SCALE = HRES / 200 #7

# Setting for hit animation
if TICKRATE < 100:
    KABOOMCONSTANT = 12
else:
    KABOOMCONSTANT = 7    # Hit explosion speed factor

CRATER_COLOR = (255, 240, 0)
BLASTSIZE = 27

#screen_color = (0, 0, 0)
GROUND_COLOR = (255, 0, 0)
PROJECTILE_COLOR = (25, 25, 25)

# Player generator setup
DEFAULT_COLOR = ((0, 0, 255), (86, 130, 3),(255, 0, 0))
#P1COLOR = (0, 0, 255)
#P2COLOR = (86, 130, 0)

# Init Pygame
pygame.init()
screen = pygame.display.set_mode((HRES, VRES))
clock = pygame.time.Clock()

# Load Fonts
title_font = pygame.font.Font('freesansbold.ttf', 64)
font1 = pygame.font.Font('freesansbold.ttf', 24)
font2 = pygame.font.Font('freesansbold.ttf', 32)
font_fps = pygame.font.Font('freesansbold.ttf', 16)
font_small = pygame.font.Font('freesansbold.ttf', 16)


###################################################################################

# def main():
async def main():

    # Initialise game objects
    fps = Frame_counter()
    world = World()
    projectile = Projectile()
    p1 = Player()
    p2 = Player()
    #print(Player.count, f"Players: {Player.list[0].name}, {Player.list[1].name};")

    
    # Game loop
    while True :
        clock.tick(TICKRATE)
        #clock.tick_busy_loop(TICKRATE)
        #time = pygame.time.get_ticks()
        Player.active = Player.list[State.turn % len(Player.list)]

        # Get mouse position 
        mouse_pos = pygame.mouse.get_pos()
        
        # Menu loop
        while State.menu == True:
            clock.tick(TICKRATE)
            Menu.cursor_blink()

            # Select correct menu screen
            if State.title_menu == True :
                Menu.title(screen)
            elif State.setup_menu == True :
                Menu.setup(screen, p1, p2)
            elif State.end_menu == True :
                # implement endscreen
                State.end_menu = False
            else:
                State.menu = False
                
            await asyncio.sleep(0)

        # Events
        for event in pygame.event.get() :
            
            # Key event
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    State.init_new = True
                    State.reset_score = True
                
                if event.key == pygame.K_ESCAPE:
                    State.menu = True
                    State.setup_menu = True

            # Mousebutton event (launch projectile
            if projectile.inflight == False and projectile.hit == False :
                if event.type == pygame.MOUSEBUTTONDOWN :
                    mouse_presses = pygame.mouse.get_pressed()
                    if mouse_presses[0]:
                        print(f"FIRE AWAY!\nVelocity X/Y: {mouse_pos},   Angle: {Player.active.cannon_angle}")
                        projectile.launch(Player.active, mouse_pos)

            # Exit game on close windows button
            if event.type == pygame.QUIT:
                sys.exit()


        # Game logic
        if State.init_new == True :    # Initiate new turn
            world.generate()
            p1.gen_pos(world)
            p2.gen_pos(world)
            projectile.reset()
            projectile.hit = p1.hit = p2.hit = False
            Blast.reset()
            State.init_new = False
            if State.reset_score == True :
                p1.score = p2.score = 0
                State.reset_score = False
            

        # Calculate projectile flight and collision, hit detect.        
        if projectile.inflight == True :                # Increment if in flight.
            projectile.increment()
            projectile.check_collision(world)
            if projectile.inflight == False:
                # Projectile is not inflight anymore, so turn is over
                State.turn += 1
            if projectile.collision == True:    
                # In case projectile has had a collision.
                # Do hit detection on both players and increment score on player hit
                if projectile.check_hit(p1.pos):
                    print(f"{p1.name} was hit!")
                    p2.increase_score()                 
                    projectile.hit = p1.hit = True
                if projectile.check_hit(p2.pos):
                    print(f"{p2.name} was hit!")
                    p1.increase_score()
                    projectile.hit = p2.hit = True



        # Render logic
        pygame.Surface.fill(screen, (0, 0, 0))                          # Draw background color.
        pygame.draw.aalines(screen, world.color, False, world.ground)   # Draw world.ground.

        if projectile.inflight == True :                                        # Draw projectile if in flight.
            pygame.draw.aalines(screen, projectile.color, False, projectile.trajectory[-7:])
            pygame.draw.aalines(screen, (255, 255, 0), False, projectile.trajectory[-2:])
            #pygame.draw.circle(screen, (255, 255, 0), projectile.trajectory[-1], radius=1)
        
        # Update cannon angle for active player, according to mouse position
        Player.active.set_cannon_angle(mouse_pos)

        # Draw cannon sprites
        draw_cannon(p1)
        draw_cannon(p2)

        # Draw player sprites
        screen.blit(p1.sprite, (p1.pos[0] - 35, p1.pos[1] - 28))
        screen.blit(p2.sprite, (p2.pos[0] - 28, p2.pos[1] - 28))

        # Draw player dots (for testing purposes)
        #pygame.draw.circle(screen, p1.color, p1.pos, radius=8)
        #pygame.draw.circle(screen, p2.color, p2.pos, radius=8)    
        
        # Draw explosions in case of projectile collision with ground
        if projectile.collision == True:
            Blast.small(projectile.crater, BLASTSIZE)


        # Draw hit animation if player is hit
        
        if projectile.hit == True:
            Blast.big(projectile.crater)


        # Draw score and framerate overlays
        draw_score(screen, p1, p2)
        fps.update()
        fps.draw_framerate(screen)
        #fps.draw_frametime(screen)


        # Flip framebuffer
        pygame.display.flip()
        await asyncio.sleep(0)

################################################################################################################################


# Game classes.
class State:
    '''
    Stores global game state
    '''
    menu = True
    title_menu = True
    setup_menu = False
    pause_menu = False
    end_menu = False

    init_new = True
    reset_score = False
    turn = 0


class World:
    '''
    Generates terrain: .ground(np.array) on initiation
    '''
    def __init__(self):
        '''
        generates ground on instantiation
        '''
        ground = []
        self.color = GROUND_COLOR


    def _iteration(self, samples, hres, vres) :
        '''
        sampling for use in World.generate()
        '''
        #nr of pixels per sample
        segment = hres / (samples - 1)
        
        # Create terrain samples and average slope between samples
        samplelist = []
        slopelist = []
        for i in range(samples) :
            samplelist.append(vres - (randint((0), (16 * vres // 20))))   # y Coordinates flipped 
        for i in range(samples - 1) :
            slopelist.append((samplelist[i + 1] - samplelist[i]) / segment)

        # Create full length list of interpolated terrain, first value is samplelist[0]
        terrain = [samplelist[0]]
        for i in range(hres - 1) :
            n = int (i / segment)
            terrain.append(float(terrain[i]) + slopelist[n])
        return terrain
    

    def generate(self, minsamples=MINSAMPLES, iterations=ITERATIONS, hres=HRES, vres=VRES) :
        '''
        Generate ground
        '''
        unweightedground = np.zeros(hres)
        weightsum = 0
        for i in range(iterations) :
            samples = minsamples * (2 ** i)
            weight = 1 / (2 ** i)
            weightsum += weight
            iter = np.array(self._iteration(samples, hres, vres))
            unweightedground += (iter * weight)
        groundlist = unweightedground / weightsum
        #groundxvalues = np.array(range(hres)) 
        #ground = np.column_stack((groundxvalues, groundlist))
        self.ground = [ i for i in enumerate(groundlist)]
        


class Player:
    '''
    Player class
    instance variables: .nr, .name, .pos, .color, .score, .sprite, .cannon_angle
    Class variables: .count, .list, .active
    '''
    count = 0
    list = []
    active = None

    def __init__(self, name=False, color=False):
        Player.count += 1
        self.nr = Player.count
        self.pos = [0, 0]
        self.set_color(color)
        self.name = str(name) if name else f"Player {self.nr}"
        self.score = 0
        self.set_sprite()
        self.hit = False
        Player.list.append(self)
        

    def __str__(self):
        return 'Player nr: {}\nName: {}\nPosition: {}\nColor: {}'.format(self.nr, self.name, self.pos, self.color)
    
    def set_name(self, name):
        self.name = str(name)

    def gen_pos(self, world, hres=HRES):
        '''
        Put Player on the ground.
        randomly calculates x coordinate within bounds and calculates correct y coordinate
        '''
        if self.nr == 1:
            xpos = randint(hres // 20, 3 * hres // 20)
            pos = [xpos, world.ground[xpos][1]]   # y Coordinates flipped 
        elif self.nr == 2:
            xpos = randint(17 * hres // 20, 19 * hres // 20)
            pos = [xpos, world.ground[xpos][1]]   # y Coordinates flipped 
        else:
            raise Exception("Invalid player nr")
        self.pos = pos

    
    def set_color(self, color):
        '''
        Allows to select player color , or pick next color from default color list
        '''
        if type(color) == tuple:
            if len(color) >= 3 and max(color) < 256 and min(color) >= 0:
                self.color = color[:3]
        else:
            self.color = DEFAULT_COLOR[(self.nr-1) % len(DEFAULT_COLOR)]

    
    def set_cannon_angle(self, mouse_pos):
        '''
        Calculates the angle of the cannon sprite according to relative mouse position
        '''
        x_offset = mouse_pos[0] - self.pos[0]
        if x_offset > 0:
            self.cannon_angle = math.degrees(math.atan((self.pos[1] - mouse_pos[1]) / x_offset ))
        elif x_offset < 0:
            self.cannon_angle = 180 + math.degrees(math.atan((self.pos[1] - mouse_pos[1]) / x_offset))
        

    def increase_score(self, amount=1) :
        '''
        Increments player score by given amount
        '''
        self.score = self.score + amount


    def set_sprite(self):
        '''
        Sets player sprite, currently on of 3 built in tanks sprites
        '''
        if self.nr == 1:
            self.sprite = pygame.image.load("img/tank_blue.png").convert_alpha()
            self.cannon_sprite = pygame.image.load("img/cannon.png").convert_alpha()
            self.cannon_angle = 5
        elif self.nr == 2:
            self.sprite = pygame.transform.flip(pygame.image.load("img/tank_green.png").convert_alpha(), True, False)
            self.cannon_sprite = pygame.image.load("img/cannon.png").convert_alpha()
            self.cannon_angle = 175
        else:
            self.sprite = pygame.image.load("img/tank_pink.png").convert_alpha()
            self.cannon_sprite = pygame.image.load("img/cannon.png").convert_alpha()
            self.cannon_angle = 5
        


class Projectile:
    '''
    Initiate projectile launch
    .trajectory .pos .velocity .inflight .collision
    '''
    def __init__(self):
        self.reset()


    def reset(self):
        '''
        Reset projectile parameters
        '''
        self.inflight = False
        self.collision = False
        self.hit = False
        self.color = PROJECTILE_COLOR
        self.pos = []
        self.velocity = []
        self.trajectory = []
        self.crater = []


    def launch(self, player, mouse_pos):#, start_velocity):
        '''
        Calculates velocity from relative mouse position and fires projectile
        '''
        self.crater = []
        self.inflight = True
        self.collision = False
        self.hit = False
        self.pos = copy.copy(player.pos)
        self.pos[1] = self.pos[1] - 13 # Correction for tank sprite cannon position
        self.trajectory = [self.pos] # Start position in trajectory list
        self.velocity = [INPUT_SCALE * (mouse_pos[0] - player.pos[0]),
                         INPUT_SCALE * (mouse_pos[1] - player.pos[1])]


    def increment(self):
        '''
        Increment projectile position by one timestep.
        '''
        dt = TIME_SCALE / TICKRATE
        position = copy.copy(self.pos)
        velocity = self.velocity #copy.deepcopy(self.velocity)
        position[0] = position[0] + velocity[0] * dt
        position[1] = position[1] + velocity[1] * dt
        velocity[1] = velocity[1] - GRAVITY * dt
        self.pos = position
        self.velocity = velocity
        self.trajectory.append(position)
    

    def check_collision(self, world):
        '''
        Check for collision with world.
        in case of projectile out of bounds, left or right edge of the screen, set .inflight:False.
        In case of collision set .inflight:False and .collision:True and calculate coordinates of crater.
        '''

        # When out of bounds
        if self.pos[0] < 0 or self.pos[0] > HRES - 1 :
            self.inflight = False

        # When collision with ground
        elif self.pos[1] >= world.ground[int(self.pos[0])][1]: # y Coordinates flipped 
            self.inflight = False
            self.collision = True
            # col_list = self.pos
            # Calculate exact intersection of projectile path with ground
            pos1 = self.trajectory[-2]
            pos2 = self.trajectory[-1]
            slope_pos = (pos2[1] - pos1[1]) / (pos2[0] - pos1[0])
            
            #print("Pos1:", pos1, " Pos2", pos2)
            #print("y:", (pos2[1] - pos1[1]), " X:", (pos2[0] - pos1[0]))
            #print("Slope:", slope_pos)
            
            # Some magic intepolation to get more accurate collision position
            const = pos1[1] - (pos1[0] * slope_pos)
            l = []
            i = 0
            if pos2[0] > pos1[0] :
                while i < abs(pos2[0] - pos1[0]) :
                    i += 1
                    x = int(pos1[0]) + i
                    y = slope_pos * x + const
                    l.append([x, y])
            else :
                while i < abs(pos2[0] - pos1[0]) :
                    i += 1
                    x = int(pos1[0]) - i
                    y = slope_pos * x + const
                    l.append([x, y])

            if len(l) < 2 :
                self.crater = self.pos
            else :
                for i in l :
                    if i[1] >= world.ground[i[0]][1] :                        
                        self.crater = i
                        return
                # This should not happen
                self.crater = self.pos
                print("HIT DETECTION ANOMALY")   
                print("len l:", len(l))
                print("Pos1:", pos1, " Pos2:", pos2)
                print("Crater:", self.crater)
                        
    
    def check_hit(self, target, blast_size=25):
        '''
        Call in case of collision. Check if target coordinates have been hit
        '''
        if sum((np.array(target, dtype=float) - np.array(self.crater)) ** 2) < (blast_size ** 2) :
            self.hit = True
            return True
        else :
            return False

    # Partial implementation of rolling bomb weapon
    '''
    def roll(self):
        posx_int = int(posx_int)
        if self.ground[posx_int - 1][1] > self.ground[posx_int + 1][1] :
            while posx_int - (i + 5) > 0 :
                if self.ground[posx_int - (i + 4)] > self.ground[posx_int - i] :
                    i += 1
                    for q in range(10) :
                        output.append((posx_int - i, self.ground[posx_int - i]))
                    if hitcheck(output[-1], postarget, 10) :
                        break
                else :
                    break
        else :
            while (posx_int + (i + 5)) < HRES :
                if self.ground[posx_int + (i + 4)] > self.ground[posx_int + i] :
                    i += 1
                    for q in range(10) :
                        output.append((posx_int + i, self.ground[posx_int + i]))
                    if hitcheck(output[-1], postarget, 10) :
                        break
                else :
                    break 

        elif roll :
            i = 0
            posx_int = int(position[0])
            if world[posx_int - 1] > world[posx_int + 1] :
                while posx_int - (i + 5) > 0 :
                    if world[posx_int - (i + 4)] > world[posx_int - i] :
                        i += 1
                        for q in range(10) :
                            output.append((posx_int - i, world[posx_int - i]))
                        if hitcheck(output[-1], postarget, 10) :
                            break
                    else :
                        break
            else :
                while (posx_int + (i + 5)) < HRES :
                    if world[posx_int + (i + 4)] > world[posx_int + i] :
                        i += 1
                        for q in range(10) :
                            output.append((posx_int + i, world[posx_int + i]))
                        if hitcheck(output[-1], postarget, 10) :
                            break
                    else :
                        break
            crater = output[-1]
            output.append(crater)
            break
        '''
    
class Blast:
    kaboom = 0
    kaboomfactor = KABOOMCONSTANT

    @classmethod
    def reset(cls):
        cls.kaboom = 0
        cls.kaboomfactor = KABOOMCONSTANT

    @classmethod
    def small(cls, crater, blastsize):
        if cls.kaboom < blastsize :
            cls.kaboom += 2
            pygame.draw.circle(screen, CRATER_COLOR, crater, radius=cls.kaboom)
        else :
            pygame.draw.circle(screen, CRATER_COLOR, crater, radius=blastsize)
    
    @classmethod
    def big(cls, crater):
        global state
        cls.kaboom += cls.kaboomfactor
        cls.kaboomfactor *= 0.997
        pygame.draw.circle(screen, CRATER_COLOR, crater, radius=cls.kaboom)
        if cls.kaboom > HRES :
            cls.kaboom = 0
            cls.kaboomfactor = KABOOMCONSTANT
            State.init_new = True

    





class Menu :
    playerselect = 1
    count = 0
    p1name = ''
    p2name = ''
    cursor = 1
    cursor_count = 0

    @classmethod
    def cursor_blink(cls):
        '''
        Makes the cursor blink
        '''
        cls.cursor_count += 2
        if cls.cursor_count >= 2 * TICKRATE:
            cls.cursor_count = 0
        cls.cursor = cls.cursor_count // TICKRATE


    @classmethod
    def typing(cls, char) :
        alfabet = string.ascii_letters
        cap = pygame.key.get_pressed()[pygame.K_LSHIFT] | pygame.key.get_pressed()[pygame.K_RSHIFT]
        if 96 < char & char < 96 + len(alfabet) :
            char = char - 97
            char = alfabet[char + cap * 26]
        #elif char == 32 :
        #    char = ' '
        else :
            char = ''
        return char


    @classmethod 
    def title(cls, surface):
        '''
        Draw Title screen
        '''
        for event in pygame.event.get() :
            # Key event    
            if event.type == pygame.KEYDOWN :
                if event.key == pygame.K_RETURN :
                    State.setup_menu = True
                    State.title_menu = False
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN :
                mouse_presses = pygame.mouse.get_pressed()
                if mouse_presses[0]:
                    State.setup_menu = True
                    State.title_menu = False

        pygame.Surface.fill(screen, (0, 0, 0))

        string = 'Tank duel'
        text = title_font.render(string, True, (255,0 ,0), (0,0,0))
        textrect = text.get_rect()
        textrect.centerx = HRES // 2
        textrect.bottom = VRES // 4
        surface.blit(text, textrect)
        
        string = '(Click to start)'
        text = font_small.render(string, True, (255, 0, 0), (0,0,0))
        text2rect = text.get_rect()
        text2rect.centerx = HRES // 2
        text2rect.top = textrect.bottom + 5
        surface.blit(text, text2rect)
        
        string = '2023' #', by Kasper Vloon'
        text = font_small.render(string, True, (100, 100, 100), (0,0,0))
        textrect = text.get_rect()
        textrect.bottomright = (HRES - 10, VRES -10)
        surface.blit(text, textrect)

        pygame.display.flip() 
 

    @classmethod
    def setup(cls, surface, p1, p2) :   # Draw setup screen
        
        pygame.Surface.fill(screen, (0, 0, 0)) 
        
        if cls.playerselect == 1:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                    # Key event    
                if event.type == pygame.KEYDOWN :
                    if event.key == pygame.K_ESCAPE:
                        if State.init_new == True:
                            State.title_menu = True
                            State.setup_menu = False
                            return
                        else:
                            State.menu = False
                            State.setup_menu = False
                            return
                    # If down key go to p2 select
                    if event.key == pygame.K_DOWN:
                        if cls.p1name:
                            p1.name = cls.p1name
                        cls.playerselect = 2
                    # If backspace
                    if event.key == 8 :
                        cls.p1name = cls.p1name[:-1]
                    # If space
                    elif event.key == 32:
                        cls.p1name = cls.p1name + ' '
                        cls.p1name = cls.p1name[:10]
                    # If unicode
                    else :
                        char = event.unicode
                        char = char.strip()
                        cls.p1name = cls.p1name + char
                        cls.p1name = cls.p1name[:10]
                    # When press ENTER: Set P1 name if typed name != empty
                    # and change selector to p2
                    if event.key == pygame.K_RETURN:
                        if cls.p1name:
                            p1.name = cls.p1name
                        cls.playerselect = 2
                    
                       
        elif cls.playerselect == 2:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                # Key event    
                if event.type == pygame.KEYDOWN :
                    if event.key == pygame.K_ESCAPE:
                        if State.init_new == True:
                            State.title_menu = True
                            State.setup_menu = False
                            cls.playerselect = 1
                            return
                        else:
                            State.menu = False
                            State.setup_menu = False
                            cls.playerselect = 1
                            return
                        
                    # If up key go to p1 select
                    if event.key == pygame.K_UP:
                        if cls.p2name:
                            p2.name = cls.p2name
                        cls.playerselect = 1
                        
                    if event.key == 8 :
                        cls.p2name = cls.p2name[:-1]
                        # If space
                    elif event.key == 32:
                        cls.p1name = cls.p1name + ' '
                        cls.p1name = cls.p1name[:10]
                    else :
                        char = event.unicode
                        char = char.strip()
                        cls.p2name = cls.p2name + char
                        cls.p2name = cls.p2name[:10]
                    # When press ENTER: Set P1 name if typed name != empty
                    # exit menu and change selector back to p1
                    if event.key == pygame.K_RETURN:
                        if cls.p2name:
                            p2.name = cls.p2name
                        cls.playerselect = 1
                        State.menu = False
                        State.setup_menu = False
                        State.init_new = True
                        State.reset_score = True
        
        
        # Title line
        string = 'Name'
        text = font2.render(string, True, (255,0 ,0), (0,0,0))
        textrect = text.get_rect()
        textrect.left = HRES * 3 // 8
        textrect.bottom = VRES // 6
        surface.blit(text, textrect)

        string = '' #'Color'
        text = font2.render(string, True, (255,0 ,0), (0,0,0))
        textrect = text.get_rect()
        textrect.left = HRES * 5 // 8
        textrect.bottom = VRES // 6
        surface.blit(text, textrect)
        
        # Player 1 line
        string = 'Player {}'.format(p1.nr)
        text = font2.render(string, True, p1.color, (0,0,0))
        text2rect = text.get_rect()
        text2rect.left = HRES // 8
        text2rect.top = textrect.bottom + 20
        surface.blit(text, text2rect)
        
        string = cls.p1name[:10] + '_' * cls.cursor if cls.playerselect == 1 else cls.p1name[:10]
        text = font2.render(string, True, p1.color, (0,0,0))
        text2rect = text.get_rect()
        text2rect.left = HRES * 3 // 8
        text2rect.top = textrect.bottom + 20
        surface.blit(text, text2rect)

        # Player 2 line
        string = 'Player {}'.format(p2.nr)
        text = font2.render(string, True, p2.color, (0,0,0))
        text3rect = text.get_rect()
        text3rect.left = HRES // 8
        text3rect.top = text2rect.top + 60
        surface.blit(text, text3rect)
        
        string = cls.p2name[:10] + '_' * cls.cursor if cls.playerselect == 2 else cls.p2name[:10]
        text = font2.render(string, True, p2.color, (0,0,0))
        text3rect = text.get_rect()
        text3rect.left = HRES * 3 // 8
        text3rect.top = text2rect.top + 60
        surface.blit(text, text3rect)

        pygame.display.flip() 


class Frame_counter:
    # Setup fps counter

    def __init__(self):
        '''
        Initiate at 0
        '''
        self.frame_count = 0
        self.frame_time_count = 0
        self.frame_time_avg = '0'
        self.fps_avg = '0'
        self.update_interval = TICKRATE // 2

    def update(self):
        '''
        Update average framerate over 'update_interval' nr of frames
        '''
        frame_time = int(clock.get_time())
        if self.frame_count < self.update_interval:
            self.frame_count += 1
            self.frame_time_count += frame_time
        else:
            ft = self.frame_time_count / self.update_interval
            self.frame_time_avg = str(round(ft, 1))
            self.fps_avg = str(round(1000 / ft, 1))
            self.frame_count = 0
            self.frame_time_count = 0

    def draw_framerate(self, surface):  
        text = font_fps.render(f"{self.fps_avg} fps", True, (0, 255, 0), (0,0,0))
        textRect = text.get_rect()
        textRect.topleft = (10, 10)
        surface.blit(text, textRect)

    def draw_frametime(self, surface):
        text = font_fps.render(f"{self.frame_time_avg} ms", True, (0, 255, 0), (0,0,0))
        textRect = text.get_rect()
        textRect.topleft = (10, 10)
        surface.blit(text, textRect)


# Game methods
def draw_score(surface, p1, p2) :   # Draw Score board

    string = p1.name + '  |'
    text = font1.render(string, True, p1.color)
    textrect = text.get_rect()
    textrect.topright = (HRES // 2, 10)
    surface.blit(text, textrect)

    string = str(p1.score)
    text = font2.render(string, True, p1.color)
    text2rect = text.get_rect()
    text2rect.top = textrect.bottom + 10
    text2rect.centerx = textrect.right - 60
    surface.blit(text, text2rect)
       

    string = '|  ' + p2.name
    text = font1.render(string, True, p2.color)
    textrect = text.get_rect()
    textrect.topleft = (HRES // 2, 10)
    surface.blit(text, textrect)

    string = str(p2.score)
    text = font2.render(string, True, p2.color)
    text2rect = text.get_rect()
    text2rect.top = textrect.bottom + 10
    text2rect.centerx = textrect.left + 60
    surface.blit(text, text2rect)


def draw_cannon(player):
    cannon = pygame.transform.rotate(player.cannon_sprite, player.cannon_angle)
    w = cannon.get_width() // 2
    h = cannon.get_height() // 2
    if player.nr == 1:
        screen.blit(cannon, (player.pos[0] - w, player.pos[1] - h - 13))
        screen.blit(player.sprite, (player.pos[0] - 35, player.pos[1] - 28))
    elif player.nr == 2:
        screen.blit(cannon, (player.pos[0] - w, player.pos[1] - h - 13))
        screen.blit(player.sprite, (player.pos[0] - 28, player.pos[1] - 28))



asyncio.run(main())

#if __name__ == "__main__":
#   main()
