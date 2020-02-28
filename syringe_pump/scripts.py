#!/usr/bin/env python3
def create_pumps():
     from syringe_pump.device import Device
     from ubcs_auxiliary.threading import new_thread
     if p1 is not None:
         p1.close()
     if p3 is not None:
         p3.close()
     p1, p3 = Device(), Device()
     p1.init(1,25,100,'Y',250)
     p1.start()
     p3.init(3,25,100,'Y',250))
     p3.start()
     new_thread(p1.prime(2))
     p3.prime(2)
     return p1,p3

def inject(pumpa, pumpf,tau = 1.0, flow = 0.01, fast_flow = 0.125, ratio = 2, N=10, t = 10):
    """
    1 mm of 250um ID capillary has 49 nL of fluid.
    """
    from time import sleep
    flow_a = flow
    flow_f = flow*ratio
    pumpf.flow(0,flow_f)
    pumpa.flow(0,flow_a)
    sleep(5*N*0.049/(flow_f+flow_a))
    pumpa.flow(250,0.5)
    sleep(0.1)
    save_images(buffer,2*(1.975)/fast_flow+1+0.5)
    pumpa.abort()

    pumpf.set_speed_on_the_fly(fast_flow)
    #sleep((1)/fast_flow)

    sleep(2*(1.975)/fast_flow)
    pumpf.abort()
    sleep(1+0.5)

def save_image_loop(t,buffer, camera):
    t_s = time()
    idx = camera.frame_count
    while t_s + t > time():
        while idx >= camera.frame_count:
            sleep(0.05)
        data = camera.RGB_array
        data = data.reshape((1,3,1360,1024))
        buffer.append(data[1,3,1360,730:830])
        idx+=1

def save_images(buffer,t = 10):
    sys.path.append('z:\\all projects\\aps\\instrumentation\\software\\lauecollect\\')
    from GigE_camera_client import Camera
    camera = Camera('MicrofluidicsCamera')
    camera.exposure_time = 0.001
    camera.stream_bytes_per_second = 1392640
    from ubcs_auxiliary.threading import new_thread
    new_thread(save_image_loop,t,buffer,camera)


def plot(buffer,N=10):
    # Creates two subplots and unpacks the output array immediately
    f, (lst) = plt.subplots(N, 1, sharey=True)
    i = 0
    for axis in lst:
        arr = 765-buffer.buffer[i,:,:,:].sum(axis=0)
        axis.imshow(arr.T,vmin = 600,vmax = 800)
        i+=1
    plt.show()

def plot_2(buffer,N=10, background = None, root = '', show = False, comments = ''):
   from numpy import concatenate
   arr = []
   for i in range(N):
       if background is not None:
           arr.append((buffer.buffer[i,:,:,:].sum(axis=0)).T-background.sum(axis=0).T)
       else:
           arr.append((buffer.buffer[i,:,:,:].sum(axis=0)).T)
   data = concatenate(arr)
   fig = plt.figure(figsize = (10,20))
   plt.imshow(-data, aspect='auto', vmin = 0, vmax = 100)
   from tempfile import gettempdir
   root = "Y:/trash/microfluidics"#gettempdir()
   suffix = '.png'
   filename = os.path.join(root, comments + suffix)
   plt.savefig(filename)
   from ubcs_auxiliary.save_load_object import save_to_file
   filename = os.path.join(root, comments + '.npy')
   dic = {}
   dic['buffer'] = buffer.buffer
   dic['comments'] = comments
   dic['background'] = background
   dic['image'] = -data
   save_to_file(filename, dic)
   if show:
       plt.show()
   else:
       plt.close(fig)


def get_background():
    from numpy import array
    sys.path.append('z:\\all projects\\aps\\instrumentation\\software\\lauecollect\\')
    from GigE_camera_client import Camera
    camera = Camera('MicrofluidicsCamera')
    data = camera.RGB_array
    return array(data[:,:,625:745])

from numpy import nan

def read_dict(filename):
    from ubcs_auxiliary.save_load_object import load_from_file
    return load_from_file(filename)

set_speed_on_the_fly(0.002)
def func(i, flow, ratio):
	flow = flow; ratio = ratio; buffer.buffer.fill(0);buffer.reset();inject(pumpa = p3,pumpf = p1,tau = 0.0, flow = flow, ratio = ratio, N = 7, t = 60); plot_2(buffer,60,bck, comments = f'exp {i} flow {flow} ratio {ratio}')

from circular_buffer_numpy.circular_buffer import CircularBuffer
buffer = CircularBuffer(shape = (20,3,1360,120))

def load_buffer(filename):
    from ubcs_auxiliary.save_load_object import load_from_file
    data = load_from_file(filename)

if __name__ == '__main__':
    from tempfile import gettempdir
    import logging;
    logging.basicConfig(filename=gettempdir()+'/scripts.log',
                        level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s: %(message)s")
    from sys import platform
    if platform == "linux" or platform == "linux2":
        # linux
    elif platform == "darwin":
        sys.path.append('/net/femto/C/All Projects/APS/Instrumentation/Software/Lauecollect/')
    elif platform == "win32":
        sys.path.append('z:\\all projects\\aps\\instrumentation\\software\\lauecollect\\')

    from GigE_camera_client import Camera
    camera = Camera('MicrofluidicsCamera')
    data = camera.RGB_array
    from matplotlib import pyplot as plt
    anchors = [(0,730),(1360,830)]
    import matplotlib.patches as patches
    # Create figure and axes
    fig,ax = plt.subplots(1)
    # Display the image
    ax.imshow(data)
    # Create a Rectangle patch
    rect = patches.Rectangle(anchors[0],40,30,linewidth=1,edgecolor='r',facecolor='none')

    # Add the patch to the Axes
    ax.add_patch(rect)
    from syringe_pump import Device
