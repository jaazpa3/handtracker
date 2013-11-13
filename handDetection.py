""""Run a webcam hand tracking program to control computer volume and mouse behavior"""
 
#imports necessary modules - cv for video, os and sys for os integration, and time for timing motions
import cv
import os
import sys
import time
import math
from subprocess import Popen, PIPE
from Xlib.display import Display
from Xlib.ext.xtest import fake_input
from Xlib.ext import record
from Xlib.X import ButtonPress,ButtonRelease
from Tkinter import *
 
 
def skin(img,ccolor):
    """Skin detection function, takes rgb image as input"""
 
    #initializes range of skin colors based on first input
    COLOR_MIN = cv.Scalar(ccolor[0]-60, ccolor[1]-10, ccolor[2]-40)
    COLOR_MAX = cv.Scalar(ccolor[0]+60, ccolor[1]+10, ccolor[2]+40)
 
    #blurs image
    cv.Smooth(img, img, cv.CV_GAUSSIAN, 9, 9)
 
    #makes new image and converts input to YcrCb
    ycrcb = cv.CreateImage(cv.GetSize(img), 8, 3)
    cv.CvtColor(img, ycrcb, cv.CV_BGR2YCrCb)
 
    #makes a black/white mask of skintone regions of the original image
    color_mask = cv.CreateImage(cv.GetSize(ycrcb), 8, 1)
    cv.InRangeS(ycrcb, COLOR_MIN, COLOR_MAX, color_mask)
  
    #returns black-white skin mask
    return color_mask
 
def setup(flipped,capture,thehandcolor):
    """Initializes camera and finds initial skin tone"""
 
    #creates initial window and prepares text
    color=(40,0,0);
    font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX,1.0,1.0);
    textsize1 = (cv.GetSize(flipped)[0]/2-150,cv.GetSize(flipped)[1]/2-140);
    textsize2 = (cv.GetSize(flipped)[0]/2-150,cv.GetSize(flipped)[1]/2-110);
    point1 = (cv.GetSize(flipped)[0]/2-25,cv.GetSize(flipped)[1]/2-25);
    point2 = (cv.GetSize(flipped)[0]/2+25,cv.GetSize(flipped)[1]/2+25);
 
    #until Enter is pressed
    while(cv.WaitKey(10)!=10):
 
        #captures live video, and draws sub-box and text
        frame = cv.QueryFrame(capture);
        cv.Copy(frame,flipped);
        cv.Flip(flipped,flipped,1);
        cv.Rectangle(flipped,point1,point2,color,2);
        cv.PutText(flipped,"Put your hand in the box ",textsize1,font,color);
        cv.PutText(flipped,"and press enter",textsize2,font,color);
        cv.ShowImage("w2",flipped);
 
    #Creates sub-image inside box, and returns average color in box
    sub = cv.GetSubRect(flipped,(cv.GetSize(flipped)[0]/2-25,cv.GetSize(flipped)[1]/2-25, 50, 50));
    cv.Set(thehandcolor,cv.Avg(sub))
    return cv.Avg(sub);
 
def bgr_ycrcb(averagetone):
    """Converts a scalar bgr color to YCrCb color space"""
 
    #unpacks input tuple
    B = averagetone[0]
    G = averagetone[1]
    R = averagetone[2]
 
    #runs through conversion equations between color spaces
    delta= 128
    y = ( 0.299 * R + 0.587 * G + 0.114 * B);
    cr = (R-y)*0.713+delta #( 0.50000 * R - 0.41869 * G - 0.08131 * B);
    cb = (B-y)*0.564+delta #(-0.16874 * R - 0.33126 * G + 0.50000 * B);
     
    #repacks and returns output
    ycrcb= [y,cr,cb]
    return ycrcb
 
 
def volcon():
    """Runs volume control portion of code"""
     
    def repeat(begin,unmute,last,hold,beginhold):
        """Actual finger detection function, passes mute and click status"""
             
        #captures input frame
        frame = cv.QueryFrame(capture)
 
        #creates horizontally flipped copy of input frame to work with
        cv.Copy(frame,sframe)
        cv.Flip(sframe,sframe,1)
 
        #makes mask of skintones
        dog = skin(sframe,ccolor)
 
        #inverts skintone mask to all non-skin areas
        cv.ConvertScale(dog, dog, -1, 255)
 
        #makes greyscale copy of frame
        cv.CvtColor(sframe,grey,cv.CV_BGR2GRAY)
 
        #replaces nonskin areas with white
        cv.Add(grey,white, grey,dog)
 
        #implements laplacian edge detection on greyscale image
        dst_16s2 = cv.CreateImage(cv.GetSize(bg), cv.IPL_DEPTH_16S, 1)
        cv.Laplace(grey, dst_16s2,5)
        cv.Convert(dst_16s2,grey)
 
        #creates a threshold to binarize the image
        cv.Threshold(grey,grey,75,255,cv.CV_THRESH_BINARY)
 
        #creates contours on greyscale image
        storage = cv.CreateMemStorage(0)
        contours = cv.FindContours (grey, storage, cv.CV_RETR_TREE , cv.CV_CHAIN_APPROX_SIMPLE)
 
        #sets final display frame background to black
        cv.Set(cframe,0)
 
        #sets minimum range for object detection
        mx = 20000
        #initializes hand position to previous
        best = last
        #creates some cvSeq maxcont by copying contours
        maxcont = contours
 
        #goes through all contours and finds bounding box
        while contours:
            bound_rect = cv.BoundingRect(list(contours))
 
            #if bounding box area is greater than min range or current max box
            if bound_rect[3]*bound_rect[2] > mx:
 
                #sets max to current object, creates position at center of box, and sets display contour to current
                mx = bound_rect[3]*bound_rect[2]
                maxcont = contours
         
            #goes to next contour
            contours = contours.h_next()
                      
        #draws largest contour on final frame
        cv.DrawContours(cframe, maxcont, 255, 127, 0)
 
        if maxcont:
            #creates convex hull of largest contour
            chull = cv.ConvexHull2(maxcont,storage,cv.CV_CLOCKWISE,1)
            cv.PolyLine(cframe,[chull],1,255)
            chulllist = list(chull)
            chull = cv.ConvexHull2(maxcont,storage,cv.CV_CLOCKWISE,0)
            cdefects = cv.ConvexityDefects(maxcont,chull,storage)
 
            #filters small convexity defects and draws large ones
            truedefects = []
            for j in cdefects:
                    if j[3] > 30:
                        truedefects.append(j)
                        cv.Circle(cframe,j[2],6,255)
 
            #if hand is in a pointer position, detects tip of convex hull
            if cdefects and len(truedefects) < 4:
                tipheight = 481
                tiploc = 0
                for j in chulllist:
                    if j[1] < tipheight:
                        tipheight = j[1]
                        tiploc = chulllist.index(j)
                best = chulllist[tiploc]
          
        #keeps last position if movement too quick, or smooths slower movement
        xdiff=best[0]-last[0]
        ydiff=best[1]-last[1]
        dist=math.sqrt(xdiff**2+ydiff**2)
        if dist > 100:
            best = last
        else:
            best = (last[0]+xdiff*.75,last[1]+ydiff*.75)
 
        #draws main position circle
        cv.Circle(cframe,(int(best[0]),int(best[1])),20,255)
           
        #displays image with contours
        cv.ShowImage("w2",cframe)
        cv.MoveWindow('w2',600,0)
        #delay between frame capture
        c = cv.WaitKey(10)
 
        if not hold:
            #if largest contour covers half the screen
            if mx > 153600/2:
                #begins timer if not yet started
                if begin == 0: begin = time.time()
                else:
                     
                    #sets volume to new volume, or 0 if muted
                    #in Linux
                    if sysname== True:
                        os.system('amixer set Master %s' % (.64*unmute*(100-best[1]/4.8)))
                    #in Mac
                    else:
                        os.system('osascript -e \'set volume output volume %s\'' %(.64*unmute*(100-best[1]/4.8)))
 
                    #if 3 seconds have passed, stops timer and switches mute status
                    if time.time()-begin > 3:
                        unmute = 1-unmute
                        begin = 0
 
            #stops timer and sets volume to new, if unmuted
            else:
                begin = 0
                #in Linux
                if sysname== True:
                    os.system('amixer set Master %s' % (int(.64*unmute*(100-best[1]/4.8))*.75))
                #in Mac
                else:
                    os.system('osascript -e \'set volume output volume %s\'' %(int(.64*unmute*(100-best[1]/4.8))*.75))
         
        #returns timer start, mute status, and previous hand position        
        return(begin,unmute,best,hold,beginhold)
         
 
    #button.configure(text = "Mouse Control", command=mousecon)
        #Systemname True= Linux False= Mac
    stdout = Popen('uname -a', shell=True,stdout=PIPE).stdout
    systemname= stdout.read();
    sysname= True
    if 'Mac' in systemname:
        sysname= False
    else:
        sysname= True
 
    #goes through all potential cameras to choose working camera
    for i in range(3):
        capture = cv.CaptureFromCAM(i)
        if capture: break
 
    #takes initial picture of background
    bg = cv.QueryFrame(capture)
 
    #creates static white image
    white = cv.CreateImage((640,480),8,1)
    cv.Set(white,255);
 
    #creates temporary variables
    sframe = cv.CreateImage((640,480),8,3)
    thehandcolor = cv.CreateImage(cv.GetSize(bg),8,3)
    flipped = cv.CreateImage(cv.GetSize(bg),8,3)
    dog = cv.CreateImage(cv.GetSize(bg),8,1)
    grey=cv.CreateImage(cv.GetSize(bg),8,1)
    cframe = cv.CreateImage(cv.GetSize(bg), 8, 1)
 
    #initializes variables for motion start time, mute status, and previous hand position
    begin = 0.0
    unmute = True
    last = (320,240)
    hold = False
    beginhold = 0.0
 
    d= Display()
    s= d.screen()
    root= s.root
     
    #runs initialization function, then volume control until escape is pressed
    ccolor= bgr_ycrcb(setup(flipped,capture,thehandcolor))
    while cv.WaitKey(10) != 27:
        begin,unmute,last,hold,beginhold = repeat(begin,unmute,last,hold,beginhold)
 
 
def mousecon():
    """Runs function for mouse control"""
 
    def repeat1(begin,unmute,last,hold,beginhold):
        """actual function for moving and clicking mouse"""
 
        def click_down():
            """Simulates a down click"""
            fake_input(d,ButtonPress,1)
            d.sync()
             
        def click_up():
            """Simulates an up click"""
            fake_input(d,ButtonRelease,1)
            d.sync()
 
        #captures input frame
        frame = cv.QueryFrame(capture)
 
        #initializes mouse behavior
        d= Display()
        s= d.screen()
        root= s.root
 
        #creates horizontally flipped copy of input frame to work with
        cv.Copy(frame,sframe)
        cv.Flip(sframe,sframe,1)
 
        #makes mask of skintones
        dog = skin(sframe,ccolor)
 
        #inverts skintone mask to all non-skin areas
        cv.ConvertScale(dog, dog, -1, 255)
 
        #makes greyscale copy of frame
        cv.CvtColor(sframe,grey,cv.CV_BGR2GRAY)
 
        #replaces nonskin areas with white
        cv.Add(grey,white, grey,dog)
 
        #implements laplacian edge detection on greyscale image
        dst_16s2 = cv.CreateImage(cv.GetSize(bg), cv.IPL_DEPTH_16S, 1)
        cv.Laplace(grey, dst_16s2,5)
        cv.Convert(dst_16s2,grey)
 
        #creates a threshold to binarize the image
        cv.Threshold(grey,grey,75,255,cv.CV_THRESH_BINARY)
 
        #creates contours on greyscale image
        storage = cv.CreateMemStorage(0)
        contours = cv.FindContours (grey, storage, cv.CV_RETR_TREE , cv.CV_CHAIN_APPROX_SIMPLE)
 
        #sets final display frame background to black
        cv.Set(cframe,0)
 
        #sets minimum range for object detection
        mx = 20000
        #initializes hand position to previous
        best = last
        #creates some cvSeq maxcont by copying contours
        maxcont = contours
 
        #goes through all contours and finds bounding box
        while contours:
            bound_rect = cv.BoundingRect(list(contours))
 
            #if bounding box area is greater than min range or current max box
            if bound_rect[3]*bound_rect[2] > mx:
 
                #sets max to current object, creates position at center of box, and sets display contour to current
                mx = bound_rect[3]*bound_rect[2]
                maxcont = contours
         
            #goes to next contour
            contours = contours.h_next()
 
        #draws largest contour on final frame
        cv.DrawContours(cframe, maxcont, 255, 127, 0)
 
        if maxcont:
            #draws and finds convex hull and convexity defects
            chull = cv.ConvexHull2(maxcont,storage,cv.CV_CLOCKWISE,1)
            cv.PolyLine(cframe,[chull],1,255)
            chulllist = list(chull)
            chull = cv.ConvexHull2(maxcont,storage,cv.CV_CLOCKWISE,0)
            cdefects = cv.ConvexityDefects(maxcont,chull,storage)
 
            #filters smaller convexity defects and displays larger ones
            truedefects = []
            for j in cdefects:
                    if j[3] > 30:
                        truedefects.append(j)
                        cv.Circle(cframe,j[2],6,255)
 
            #Finds highest point of convex hull if hand follows smooth vertical shape
            if cdefects and len(truedefects) < 4:
                tipheight = 481
                tiploc = 0
                for j in chulllist:
                    if j[1] < tipheight:
                        tipheight = j[1]
                        tiploc = chulllist.index(j)
                best = chulllist[tiploc]
          
            #if hand is open, begin click
            if len(truedefects) >= 4:
                if beginhold == 0:
                    beginhold = time.time()
                else:
                    #if .05 seconds have passed, clicks down
                    if (time.time()-beginhold > .05) and not hold:
                        hold = True
                        beginhold = 0
                        click_down()
 
            #unclicks if hand returns to smooth
            else:
                if hold:
                    click_up()
                    hold = False
                beginhold = 0
 
        #keeps last position if movement too quick, or smooths slower movement
        xdiff=best[0]-last[0]
        ydiff=best[1]-last[1]
        dist=math.sqrt(xdiff**2+ydiff**2)
        if dist > 100:
            best = last
        else:
            best = (last[0]+xdiff*.75,last[1]+ydiff*.75)
 
        #displays main position circle
        cv.Circle(cframe,(int(best[0]),int(best[1])),20,255)
        #displays image with contours
        cv.ShowImage("w2",cframe)
        cv.MoveWindow('w2',500,0)
        #delay between frame capture
        c = cv.WaitKey(10)
 
        #Mouse Move/ Bottom Pointer
        Dx,Dy= mousedelta(last,best)
        root.warp_pointer((best[0]-320)*1600/600+800,best[1]*900/360)
        d.sync()
 
        return(begin,unmute,best,hold,beginhold)
             
    def mousedelta(pos1,pos2):
        """finds difference between current mouse position and last"""
        x0= pos1[0]
        y0= pos1[1]
        x= pos2[0]
        y= pos2[1]
        dx,dy = x-x0, y-y0
        Dx= dx
        Dy= dy
        return Dx, Dy
         
 
    #button.configure(text = "Volume Control", command=volcon)
    #Systemname True= Linux False= Mac
    stdout = Popen('uname -a', shell=True,stdout=PIPE).stdout
    systemname= stdout.read();
    sysname= True
    if 'Mac' in systemname:
        sysname= False
    else:
        sysname= True
 
 
    #goes through all potential cameras to choose working camera
    for i in range(3):
        capture = cv.CaptureFromCAM(i)
        if capture: break
 
    #takes initihttp://code.activestate.com/recipes/578104-openkinect-mouse-control-using-python/al picture of background
    bg = cv.QueryFrame(capture)
 
    #creates static white image
    white = cv.CreateImage(cv.GetSize(bg),8,1)
    cv.Set(white,255);
 
    #creates temporary variables
    sframe = cv.CreateImage(cv.GetSize(bg),8,3)
    thehandcolor = cv.CreateImage(cv.GetSize(bg),8,3)
    flipped = cv.CreateImage(cv.GetSize(bg),8,3)
    dog = cv.CreateImage(cv.GetSize(bg),8,1)
    grey=cv.CreateImage(cv.GetSize(bg),8,1)
    cframe = cv.CreateImage(cv.GetSize(bg), 8, 1)
 
    #initializes variables for motion start time, mute status, and previous hand position
    begin = 0.0
    unmute = True
    last = (320,240)
    hold = False
    beginhold = 0.0
 
    #initializes skin color, then runs through mouse control
    ccolor= bgr_ycrcb(setup(flipped,capture,thehandcolor))
    cv.DestroyWindow("w3")
    while cv.WaitKey(10) != 27:
        begin,unmute,last,hold,beginhold = repeat1(begin,unmute,last,hold,beginhold)
 
if __name__== "__main__":
    """creates gui with 3 buttons for 3 different functions"""
 
    root = Tk()
    root.title('Gesture Recognition')
    root.geometry('300x30')
    guiframe = Frame(root)
    Quit = Button(guiframe,text="Quit",command=quit)
    Quit.pack(side=LEFT)
    button = Button(guiframe,text="Volume Control",command=volcon)
    button.pack(side=LEFT)
    mousePointer = Button(guiframe,text="Mouse Control",command=mousecon)
    mousePointer.pack(side=LEFT)
    guiframe.pack()
    root.mainloop()
