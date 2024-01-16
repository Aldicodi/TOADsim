#########################################################
#               Welcome to TOAD sim!                    #
#                                                       #
#   This program simulates PSP AC's TOAD vehicle        #
#   using an approximation consisting of a vectored     #
#   force (the engine), a simple rod (vehicle frame),   #
#   and three point masses with dynamic mass based on   #
#   throttle usage (propellant and pressurant tanks).   #
#   The physics simulation uses principles learned in   #
#   PHYS 172 which I am taking as I write this          #
#   program in the fall of 2023. The concepts used      #
#   include moment of inertia, torque, and basic        #
#   kinematics. Together, these provide a roughly       #
#   accurate representation of the controllability      #
#   of the vehicle based on different configurations    #
#   and mass distributions. Please check the README     #
#   file for a user guide and more info about the       #
#   program.                                            #
#                                                       #
#########################################################

## Notes ##
# Every pixel is 0.2 m, meaning that one meter is 5px
# Point rotations done following this process:
# https://www.youtube.com/watch?v=7j5yW5QDC2U 

#####################################################

## imports ##

import pygame, time
import numpy as np
import FuelInputUDF as fuelData

## Helper functions ##

#Calculates the COM based on a quadratic equation (see docs for derivation)
def COM_Calc(L, m_b, m_1, m_2, m_3, d_1, d_2, d_3):
    a = 1
    b = 2
    c = 3
    if L != 0:
        a = m_b / L
        b = m_1 + m_2 + m_3 - m_b / 2
        c = -(m_1 * d_1 + m_2 * d_2 + m_3 * d_3)

        x = [(-b + np.sqrt((b ** 2) - 4 * a * c))/(2 * a), (-b - np.sqrt((b ** 2) - 4 * a * c))/(2 * a)]
    else:
        x = [0, 0]

    return x[0]

#Calculates the coordinates of the triangle sprite's points based on specified coordinates and vehicle angle
def draw_TOAD(surface, color, height, c_x, c_y, v_theta):
    rotation_matrix = np.array([[np.cos(v_theta), -np.sin(v_theta)], [np.sin(v_theta), np.cos(v_theta)]])
    i1 = np.array([[0], [(height / 2) * 5]])
    i2 = np.array([[-(height / 4) * 5], [-(height / 2) * 5]])
    i3 = np.array([[(height / 4) * 5], [-(height / 2) * 5]])

    f1 = np.matmul(rotation_matrix, i1)
    f2 = np.matmul(rotation_matrix, i2)
    f3 = np.matmul(rotation_matrix, i3)

    pygame.draw.polygon(surface, color, [(f1[0, 0] + c_x, f1[1, 0] + c_y),(f2 [0, 0] + c_x, f2[1, 0] + c_y),(f3[0, 0] + c_x, f3[1, 0] + c_y)])

#####################################################
    
#####################################################

#Need to use one external UDF to meet project requirements
    
masses = fuelData.mass_inputs()

#####################################################

## Pygame stuff ##
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TOAD_GREEN = (51, 255, 51)
WHITE = (255, 255, 255)
LOX_BLUE = (51, 153, 255)
IPA_RED = (255, 0, 0)
N2_YELLOW = (255, 255, 0)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.Font("freesansbold.ttf", 18)
font2 = pygame.font.Font("freesansbold.ttf", 10)

## Time matching stuff ##
prev_time = time.time()
dt = 0

## Vehicle parameters ##
# All positions are relative to the engine mount at the bottom of the vehicle 
# (S.I. units; m, kg, N, rad...)
height = 2.0

frame_mass = 110 #Frame mass

fTank_pos = 1.5 #Fuel tank position
oTank_pos = 0.5 #Oxidizer tank position
pTank_pos = 1.0 #Pressurant tank position

fTank_dMass = 15 #Fuel tank dry mass
oTank_dMass = 15 #Oxidizer tank dry mass
pTank_dMass = 15 #Pressurant tank dry mass

f_mass = masses[0] #Fuel mass (20kg for default TOAD)
o_mass = masses[1] #Oxidizer mass (20kg for default TOAD)
p_mass = masses[2] #Pressurant mass (4kg for default TOAD)

f_massFlow = 0.5 #Fuel mass flow (kg/s)
o_massFlow = 0.5 #Oxidizer mass flow (kg/s)
pF_massFlow = 0.05 #Pressurant mass flow into fuel tank (kg/s)
pO_massFlow = 0.05 #Pressurant mass flow into oxidizer tank (kg/s)

max_thrust = 2446 #N, at 100% throttle
TVC_angle = 10 * (np.pi / 180) #Max angle for vectoring the engine
thr_min = 40 / 100 #Minimum throttle setting for the engine


## Physiscs simulation initial value calcs ##

fTank_wMass = fTank_dMass + f_mass #Fuel tank wet mass
oTank_wMass = oTank_dMass + o_mass #Oxidizer tank wet mass
pTank_wMass = pTank_dMass + p_mass #Pressurant tank wet mass

com = COM_Calc(height, frame_mass, fTank_wMass, oTank_wMass, pTank_wMass, fTank_pos, oTank_pos, pTank_pos) # Center of mass

m_total = fTank_wMass + oTank_wMass + pTank_wMass + frame_mass

# Distances from the COM
fTank_dcom = abs(com - fTank_pos) 
oTank_dcom = abs(com - oTank_pos)
pTank_dcom = abs(com - pTank_pos)

# Moments of inertia
#Here the frame is split into two rods due to the fact that the mass distribution may not put the
#COM at the middle of the height.
I_frame = (1 / 3) * frame_mass * ((com / height) * (com ** 2) + ((height - com) / height) * ((height - com) ** 2))

I_fTank = fTank_wMass * (fTank_dcom ** 2)
I_oTank = oTank_wMass * (oTank_dcom ** 2)
I_pTank = pTank_wMass * (pTank_dcom ** 2)

I_total = I_frame + I_fTank + I_oTank + I_pTank

## Game management ##
run = True #Run the PyGame portion of the code

throttle = 0.4 #Throttle variable to change throughout the game (begins at 0)
throttle_save = 0.4 #Allows user to change the throttle when the engine is not running
thr_step = 5 / 10000 #Adjusts the sensitivity of the throttle keys
thrust_angle = 0 #Angle at which the thrust is being produced
L_total = 0 #Used to calculate the rate of rotation and the effect of vectoring thrust. (+CCW)
P_x = 0 #Linear momentum in the x direction
P_y = 0 #Linear momentum in the y direction
vehicle_angle = 0 #Orientation of the vehicle 
cord_x = SCREEN_WIDTH / 2 #Vehicle coordinate on the x-axis (px)
cord_y = SCREEN_HEIGHT - (2 * height) #Vehicle coordinate on the y-axis (px)
pos_x = cord_x / 5 #Vehicle position on the x-axis (m)
pos_y = (SCREEN_HEIGHT - cord_y ) / 5 #Vehicle position on the y-axis (m)
T_engine = 0 #Torque produced by the engine
force_x = 0 #Used to simplify the code and avoid redundant key press checks
force_y = 0 #Used to simplify the code and avoid redundant key press checks

xflag = False #Momentum reset prevention flag
yflag = False #Momentum reset prevention flag

engine_on = False #Handles engine start control and fuel depletion
changed = False #Helps manage the engine start logic

trail = True #Activates a trail behind the vehicle
trailSize = 300 #Max number of points that will be used to draw a trail
interval = 0.2 #How much time to wait before logging a new point
timer = 0 #Keeps track of elapsed time since the last point was plotted
counter = 0 #Up to what index should be rendered (reduces content checks, do not modify)
trailCords_X = np.zeros([1, trailSize]) #Stores x coordinates of the trail points
trailCords_Y = np.zeros([1, trailSize]) #Stores the y coordinates of the trail points

while run:
    ## Pygame initial drawing ##
    screen.fill((0,0,0))
    
    text = font.render(f"Throttle: {(throttle_save * 100):.1f}%", True, WHITE)
    textRect = text.get_rect()
    textRect.topleft = (2.5, 2.5)
    screen.blit(text, textRect)

    text = font.render(f"Fuel: {(fTank_wMass - fTank_dMass):.4f} Kg", True, WHITE)
    textRect = text.get_rect()
    textRect.topleft = (2.5, 23)
    screen.blit(text, textRect)

    text = font.render(f"Pressurant: {(pTank_wMass - pTank_dMass):.4f} Kg", True, WHITE)
    textRect = text.get_rect()
    textRect.topleft = (2.5, 23+16+2.5)
    screen.blit(text, textRect)
    
    #Propellant bars
    text = font2.render("F", True, WHITE)
    textRect = text.get_rect()
    textRect.center = (SCREEN_WIDTH - 65, 150 + 35)
    screen.blit(text, textRect)
    text = font2.render("O", True, WHITE)
    textRect = text.get_rect()
    textRect.center = (SCREEN_WIDTH - 45, 150 + 35)
    screen.blit(text, textRect)
    text = font2.render("P", True, WHITE)
    textRect = text.get_rect()
    textRect.center = (SCREEN_WIDTH - 25, 150 + 35)
    screen.blit(text, textRect)
    pygame.draw.line(screen, WHITE, (SCREEN_WIDTH - 70, 24), (SCREEN_WIDTH - 20, 24), 1)
    pygame.draw.line(screen, WHITE, (SCREEN_WIDTH - 70, 37.5 + 25), (SCREEN_WIDTH - 20, 37.5 + 25), 1)
    pygame.draw.line(screen, WHITE, (SCREEN_WIDTH - 70, 75 + 25), (SCREEN_WIDTH - 20, 75 + 25), 1)
    pygame.draw.line(screen, WHITE, (SCREEN_WIDTH - 70, 112.5 + 25), (SCREEN_WIDTH - 20, 112.5 + 25), 1)
    pygame.draw.line(screen, WHITE, (SCREEN_WIDTH - 70, 150 + 26), (SCREEN_WIDTH - 20, 150 + 26), 1)
    pygame.draw.line(screen, IPA_RED, (SCREEN_WIDTH - 65, 150 + 25), (SCREEN_WIDTH - 65, 150 - 150 * ((fTank_wMass - fTank_dMass) / f_mass) + 25), 4)
    pygame.draw.line(screen, LOX_BLUE, (SCREEN_WIDTH - 45, 150 + 25), (SCREEN_WIDTH - 45, 150 - 150 * ((oTank_wMass - oTank_dMass) / o_mass) + 25), 4)
    pygame.draw.line(screen, N2_YELLOW, (SCREEN_WIDTH - 25, 150 + 25), (SCREEN_WIDTH - 25, 150 - 150 * ((pTank_wMass - pTank_dMass) / p_mass) + 25), 4)

    ## Delta Time calcs ##
    now = time.time()
    dt = now - prev_time
    prev_time = now

#####################################################

    ## Physics sim section ##

    # Update masses of the vehicle
    if (fTank_wMass - (f_massFlow - pF_massFlow) * dt * throttle > fTank_dMass and oTank_wMass - (o_massFlow - pO_massFlow) * dt * throttle > oTank_dMass and pTank_wMass - (pF_massFlow + pO_massFlow) * dt * throttle > pTank_dMass):
        fTank_wMass -= (f_massFlow - pF_massFlow) * dt * throttle
        oTank_wMass -= (o_massFlow - pO_massFlow) * dt * throttle
        pTank_wMass -= (pF_massFlow + pO_massFlow) * dt * throttle
        fTank_dMass += pF_massFlow * dt * throttle #Helps keep track of the pressurant that has entered the fuel tank
        oTank_dMass += pO_massFlow * dt * throttle #Helps keep track of the pressurant that has entered the oxidizer tank
        m_total = fTank_wMass + oTank_wMass + pTank_wMass + frame_mass
    else:
        engine_on = False #Shutdown engine if the vehicle runs out of propellant

    # Center of mass update
    com = COM_Calc(height, frame_mass, fTank_wMass, oTank_wMass, pTank_wMass, fTank_pos, oTank_pos, pTank_pos)

    fTank_dcom = abs(com - fTank_pos) 
    oTank_dcom = abs(com - oTank_pos)
    pTank_dcom = abs(com - pTank_pos)

    # Update moment of inertia of the vehicle
    I_frame = (1 / 3) * frame_mass * ((com / height) * (com ** 2) + ((height - com) / height) * ((height - com) ** 2))

    I_fTank = fTank_wMass * (fTank_dcom ** 2)
    I_oTank = oTank_wMass * (oTank_dcom ** 2)
    I_pTank = pTank_wMass * (pTank_dcom ** 2)

    I_total = I_frame + I_fTank + I_oTank + I_pTank 

    # Update angular momentum of the vehicle
    L_total += T_engine * dt #Angular impulse = torque * time. Then add to angular momentum

    # Update linear momentum. Edge of the "map" handling and gravity included
    #Delta P = throttle * thrust at 100% * delta time
    key = pygame.key.get_pressed()

    if (cord_x > SCREEN_WIDTH - height * 2.5):
        if not xflag:
            P_x = 0 #Stop the vehicle at the edge of the "map"
            xflag = True #Set momentum reset prevention flag to true

        if (force_x <= 0): #Check if the force is pushing the vehicle into the window
            P_x += force_x * dt #Calculate delta P and add to P
        else:
            xflag = False #Set the momentum reset prevention flag to false again otherwise
    elif (cord_x < height * 2.5):
        if not xflag:
            P_x = 0
            xflag = True

        if (force_x >= 0):
            P_x += force_x * dt
        else:
            xflag = False
    else:
        P_x += force_x * dt #Update momentum normally if inside window

    if (cord_y < height * 2.5):
        if not yflag:
            P_y = 0

        yflag = True

        if (force_y <= 0):
            P_y += force_y * dt
        else:
            yflag = False
    elif (cord_y >= SCREEN_HEIGHT - height * 2.5):
        if not yflag:
            P_y = 0

        yflag = True

        if (force_y >= 0):
            P_y += force_y * dt
        else: 
            yflag = False
    else:
        P_y += force_y * dt

    #Set the flags back to false once the sprite is back in the window
    if (xflag and cord_x <= SCREEN_WIDTH - height * 2.5 and cord_x >= height * 2.5): 
        xflag = False

    if (yflag and cord_y >= height * 2.5 and cord_y <= SCREEN_HEIGHT - height * 2.5):
        yflag = False

    # Update position
    pos_x += (P_x / m_total) * dt #Delta x = (P in x / total mass) * delta time
    cord_x = pos_x * 5
    pos_y += (P_y / m_total) * dt
    cord_y = SCREEN_HEIGHT - pos_y * 5
    
    # Update rotation
    vehicle_angle += (L_total / I_total) * dt #Delta omega = (L / I) * delta time

    # Throttle update
    throttle = throttle_save

    if(throttle + thr_step < 1): #Checks if throttle is within bounds
        if key[pygame.K_LSHIFT] == True:
            throttle += thr_step #Add a throttle step
    if(throttle - thr_step > thr_min):
        if key[pygame.K_LCTRL] == True:
            throttle -= thr_step
    
    throttle_save = throttle #Saves throttle to another variable so it can be changed while the engine is off

    #Engine start/stop process
    if key[pygame.K_e] == True:
        if not changed:
            if engine_on:
                engine_on = False
            else:
                engine_on = True
            changed = True
    else:
        changed = False

    if not engine_on: #If the engine is off, throttle is 0
        throttle = 0

    # Calculate torque on the vehicle
    #Torque = max thrust * throttle * distance from COM * sin(vectored angle of the engine)
    if key[pygame.K_LEFT] == True:
        T_engine = max_thrust * throttle * com * np.sin(-(TVC_angle))
    elif key[pygame.K_RIGHT] == True:
        T_engine = max_thrust * throttle * com * np.sin(TVC_angle)
    else:
        T_engine = 0

    # Update forces
    if key[pygame.K_LEFT] == True:
        force_x = np.sin(vehicle_angle - TVC_angle) * throttle * max_thrust 
        force_y = np.cos(vehicle_angle - TVC_angle) * throttle * max_thrust - 9.81 * m_total
    elif key[pygame.K_RIGHT] == True:
        force_x = np.sin(vehicle_angle + TVC_angle) * throttle * max_thrust
        force_y = np.cos(vehicle_angle + TVC_angle) * throttle * max_thrust - 9.81 * m_total
    else:
        force_x = np.sin(vehicle_angle) * throttle * max_thrust
        force_y = np.cos(vehicle_angle) * throttle * max_thrust - 9.81 * m_total

#####################################################

    ## Game update ##

    # Update the sprite
    draw_TOAD(screen, TOAD_GREEN, height, cord_x, cord_y, vehicle_angle + np.pi)

    #Altitude display on toad
    text = font2.render(f"{pos_y:.2f}m", True, WHITE)
    textRect = text.get_rect()
    textRect.topleft = (cord_x + 7, cord_y - 5)
    screen.blit(text, textRect)
    
    # Update the trail
    if counter < trailSize and timer >= interval and trail:
        trailCords_X[0, counter] = cord_x
        trailCords_Y[0, counter] = cord_y
        counter += 1
        timer = 0
    elif counter < trailSize and timer < interval and trail:
        timer += dt

    #Draw the trail segments by looping through the coordinate arrays
    for i in range(1, counter - 1):
        pygame.draw.line(screen, WHITE, (trailCords_X[0, i], trailCords_Y[0, i]), (trailCords_X[0, i + 1], trailCords_Y[0, i + 1]))

    # PyGame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    pygame.display.update()

pygame.quit()