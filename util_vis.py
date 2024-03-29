import numpy as np
import os,sys,time
import torch
import torch.nn.functional as torch_F
import torchvision
import torchvision.transforms.functional as torchvision_F
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import PIL
import imageio
from easydict import EasyDict as edict

import camera
import matplotlib.ticker as ticker

@torch.no_grad()
def tb_image(opt,tb,step,group,name,images,num_vis=None,from_range=(0,1),cmap="gray"):
    images = preprocess_vis_image(opt,images,from_range=from_range,cmap=cmap)
    num_H,num_W = num_vis or opt.tb.num_images
    images = images[:num_H*num_W]
    image_grid = torchvision.utils.make_grid(images[:,:3],nrow=num_W,pad_value=1.)
    if images.shape[1]==4:
        mask_grid = torchvision.utils.make_grid(images[:,3:],nrow=num_W,pad_value=1.)[:1]
        image_grid = torch.cat([image_grid,mask_grid],dim=0)
    tag = "{0}/{1}".format(group,name)
    tb.add_image(tag,image_grid,step)

def preprocess_vis_image(opt,images,from_range=(0,1),cmap="gray"):
    min,max = from_range
    images = (images-min)/(max-min)
    images = images.clamp(min=0,max=1).cpu()
    if images.shape[1]==1:
        images = get_heatmap(opt,images[:,0].cpu(),cmap=cmap)
    return images

def dump_images(opt,idx,name,images,masks=None,from_range=(0,1),cmap="gray"):
    images = preprocess_vis_image(opt,images,masks=masks,from_range=from_range,cmap=cmap) # [B,3,H,W]
    images = images.cpu().permute(0,2,3,1).numpy() # [B,H,W,3]
    for i,img in zip(idx,images):
        fname = "{}/dump/{}_{}.png".format(opt.output_path,i,name)
        img_uint8 = (img*255).astype(np.uint8)
        imageio.imsave(fname,img_uint8)

def get_heatmap(opt,gray,cmap): # [N,H,W]
    color = plt.get_cmap(cmap)(gray.numpy())
    color = torch.from_numpy(color[...,:3]).permute(0,3,1,2).float() # [N,3,H,W]
    return color

def color_border(images,colors,width=3):
    images_pad = []
    for i,image in enumerate(images):
        image_pad = torch.ones(3,image.shape[1]+width*2,image.shape[2]+width*2)*(colors[i,:,None,None]/255.0)
        image_pad[:,width:-width,width:-width] = image
        images_pad.append(image_pad)
    images_pad = torch.stack(images_pad,dim=0)
    return images_pad

@torch.no_grad()
def vis_cameras(opt,vis,step,poses=[],colors=["blue","magenta"],plot_dist=True):
    win_name = "{}/{}".format(opt.group,opt.name)
    data = []
    # set up plots
    centers = []
    for pose,color in zip(poses,colors):
        pose = pose.detach().cpu()
        vertices,faces,wireframe = get_camera_mesh(pose,depth=opt.visdom.cam_depth)
        center = vertices[:,-1]
        centers.append(center)
        # camera centers
        data.append(dict(
            type="scatter3d",
            x=[float(n) for n in center[:,0]],
            y=[float(n) for n in center[:,1]],
            z=[float(n) for n in center[:,2]],
            mode="markers",
            marker=dict(color=color,size=3),
        ))
        # colored camera mesh
        vertices_merged,faces_merged = merge_meshes(vertices,faces)
        data.append(dict(
            type="mesh3d",
            x=[float(n) for n in vertices_merged[:,0]],
            y=[float(n) for n in vertices_merged[:,1]],
            z=[float(n) for n in vertices_merged[:,2]],
            i=[int(n) for n in faces_merged[:,0]],
            j=[int(n) for n in faces_merged[:,1]],
            k=[int(n) for n in faces_merged[:,2]],
            flatshading=True,
            color=color,
            opacity=0.05,
        ))
        # camera wireframe
        wireframe_merged = merge_wireframes(wireframe)
        data.append(dict(
            type="scatter3d",
            x=wireframe_merged[0],
            y=wireframe_merged[1],
            z=wireframe_merged[2],
            mode="lines",
            line=dict(color=color,),
            opacity=0.3,
        ))
    if plot_dist:
        # distance between two poses (camera centers)
        center_merged = merge_centers(centers[:2])
        data.append(dict(
            type="scatter3d",
            x=center_merged[0],
            y=center_merged[1],
            z=center_merged[2],
            mode="lines",
            line=dict(color="red",width=4,),
        ))
        if len(centers)==4:
            center_merged = merge_centers(centers[2:4])
            data.append(dict(
                type="scatter3d",
                x=center_merged[0],
                y=center_merged[1],
                z=center_merged[2],
                mode="lines",
                line=dict(color="red",width=4,),
            ))
    # send data to visdom
    vis._send(dict(
        data=data,
        win="poses",
        eid=win_name,
        layout=dict(
            title="({})".format(step),
            autosize=True,
            margin=dict(l=30,r=30,b=30,t=30,),
            showlegend=False,
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            )
        ),
        opts=dict(title="{} poses ({})".format(win_name,step),),
    ))

def get_camera_mesh(pose,depth=1):
    #TODO camera size control
    z = 0.1
    x = 0.1
    vertices = torch.tensor([[-x,-x,z],
                             [x,-x,z],
                             [x,x,z],
                             [-0.1,0.1,z],
                             [0,0,0]])*depth
    faces = torch.tensor([[0,1,2],
                          [0,2,3],
                          [0,1,4],
                          [1,2,4],
                          [2,3,4],
                          [3,0,4]])

    #origin
    vertices = torch.tensor([[-0.5,-0.5,1],
                             [0.5,-0.5,1],
                             [0.5,0.5,1],
                             [-0.5,0.5,1],
                             [0,0,0]])*depth
    faces = torch.tensor([[0,1,2],
                          [0,2,3],
                          [0,1,4],
                          [1,2,4],
                          [2,3,4],
                          [3,0,4]])
    vertices = camera.cam2world(vertices[None],pose)
    wireframe = vertices[:,[0,1,2,3,0,4,1,2,4,3]]
    return vertices,faces,wireframe


def merge_wireframes(wireframe):
    wireframe_merged = [[],[],[]]
    for w in wireframe:
        wireframe_merged[0] += [float(n) for n in w[:,0]]+[None]
        wireframe_merged[1] += [float(n) for n in w[:,1]]+[None]
        wireframe_merged[2] += [float(n) for n in w[:,2]]+[None]
    return wireframe_merged
def merge_meshes(vertices,faces):
    mesh_N,vertex_N = vertices.shape[:2]
    faces_merged = torch.cat([faces+i*vertex_N for i in range(mesh_N)],dim=0)
    vertices_merged = vertices.view(-1,vertices.shape[-1])
    return vertices_merged,faces_merged
def merge_centers(centers):
    center_merged = [[],[],[]]
    for c1,c2 in zip(*centers):
        center_merged[0] += [float(c1[0]),float(c2[0]),None]
        center_merged[1] += [float(c1[1]),float(c2[1]),None]
        center_merged[2] += [float(c1[2]),float(c2[2]),None]
    return center_merged

def plot_save_optim_poses(opt, fig, pose, pose_ref=None, path=None, ep=None):
    # get the camera meshes
    _, _, cam = get_camera_mesh(pose, depth=opt.visdom.cam_depth)
    cam = cam.numpy()
    if pose_ref is not None:
        _, _, cam_ref = get_camera_mesh(pose_ref, depth=opt.visdom.cam_depth)
        cam_ref = cam_ref.numpy()  # (N,10,3)
    # set up plot window(s)
    plt.title("epoch {}".format(ep))
    ax1 = fig.add_subplot(131, projection="3d")
    ax2 = fig.add_subplot(132, projection="3d")
    ax3 = fig.add_subplot(133, projection="3d")

    x_max = np.max([np.max(cam_ref[:, 5, 0]), np.max(cam[:, 5, 0])] )+0.1
    x_min = np.min([np.min(cam_ref[:, 5, 0]), np.min(cam[:, 5, 0])] )-0.1
    y_max = np.max([np.max(cam_ref[:, 5, 1]), np.max(cam[:, 5, 1])] )+0.1
    y_min = np.min([np.min(cam_ref[:, 5, 1]), np.min(cam[:, 5, 1])] )-0.1
    z_max = np.max([np.max(cam_ref[:, 5, 2]), np.max(cam[:, 5, 2])])+0.05
    z_min = np.min([np.min(cam_ref[:, 5, 2]), np.min(cam[:, 5, 2])])-0.05

    setup_3D_plot(ax1, elev=-90, azim=-90, lim=edict(x=(x_min, x_max), y=(y_min, y_max), z=(z_min, z_max)))  # x=(-1,1),y=(-1,1),z=(-1,1)
    setup_3D_plot(ax2, elev=0, azim=-90, lim=edict(x=(x_min, x_max), y=(y_min, y_max), z=(z_min, z_max)))
    setup_3D_plot(ax3, elev=-90, azim=-90, lim=edict(x=(x_min, x_max), y=(y_min, y_max), z=(z_min, z_max)))  # x=(-1,1),y=(-1,1),z=(-1,1)


    ax1.set_title("forward-facing view", pad=0, fontsize=18)
    ax2.set_title("top-down view", pad=0, fontsize=18)
    ax3.set_title("forward-facing view", pad=0, fontsize=18)
    plt.subplots_adjust(left=0, right=1, bottom=0, top=0.95, wspace=0, hspace=0)
    plt.margins(tight=True, x=0, y=0)
    # plot the cameras
    N = len(cam)
    color = plt.get_cmap("gist_rainbow")

    arkit_color = (0.1,0.65,0.65)
    # plt.plot(arkit_step, arkit_psnr, label='Ours', c=(00, 139 / 255.0, 139 / 255.0))
    # plt.plot(iphone_step, iphone_psnr, label='BARF', c=(255 / 255.0, 99 / 255.0, 71 / 255.0))
    for i in range(N):
        if pose_ref is not None:
            ref_color = (0.3, 0.3, 0.3)
            # ref_color = (0.7, 0.2, 0.7)
            ax1.plot(cam_ref[i, :, 0], cam_ref[i, :, 1], cam_ref[i, :, 2], color=ref_color, linewidth=1)
            ax2.plot(cam_ref[i, :, 0], cam_ref[i, :, 1], cam_ref[i, :, 2], color=ref_color, linewidth=1)
            ax1.scatter(cam_ref[i, 5, 0], cam_ref[i, 5, 1], cam_ref[i, 5, 2], color=ref_color, s=40)
            ax2.scatter(cam_ref[i, 5, 0], cam_ref[i, 5, 1], cam_ref[i, 5, 2], color=ref_color, s=40)

        c = np.array(color(float(i)/N))*0.8
        c=arkit_color

        ax1.plot(cam[i, :, 0], cam[i, :, 1], cam[i, :, 2], color=c)
        ax2.plot(cam[i, :, 0], cam[i, :, 1], cam[i, :, 2], color=c)
        ax1.scatter(cam[i, 5, 0], cam[i, 5, 1], cam[i, 5, 2], color=c, s=40)
        ax2.scatter(cam[i, 5, 0], cam[i, 5, 1], cam[i, 5, 2], color=c, s=40)

    ax3.plot(cam_ref[:, 5, 0], cam_ref[:, 5, 1], cam_ref[:, 5, 2],c=ref_color ,label='GT')
    ax3.plot(cam[:, 5, 0], cam[:, 5, 1], cam[:, 5, 2],c=arkit_color, label='Ours',markersize=5)  # linestyle='-' 'rx:'
    ax3.scatter(cam_ref[:, 5, 0], cam_ref[:, 5, 1], cam_ref[:, 5, 2],c=ref_color ,s=40)  # linestyle='-' ,'cx--'
    ax3.scatter(cam[:, 5, 0], cam[:, 5, 1], cam[:, 5, 2],c=arkit_color,s=40)  # linestyle='-' 'rx:'
    ax3.legend(loc=(0.22,0.72))


    ax1.xaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax1.zaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax1.xaxis.set_minor_locator(ticker.MultipleLocator(0.1))

    ax2.xaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax2.zaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax2.xaxis.set_minor_locator(ticker.MultipleLocator(0.1))

    ax3.xaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax3.yaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax3.zaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax3.xaxis.set_minor_locator(ticker.MultipleLocator(0.1))


    png_fname = "{}/{}.png".format(path, ep)
    plt.savefig(png_fname, dpi=75)
    # clean up
    plt.clf()

def plot_save_poses(opt, fig, pose, pose_ref=None, path=None, ep=None):
    # get the camera meshes
    # print("plot_save!!!  pose shape ",pose.shape)
    _, _, cam = get_camera_mesh(pose, depth=opt.visdom.cam_depth)
    cam = cam.numpy()
    if pose_ref is not None:
        _, _, cam_ref = get_camera_mesh(pose_ref, depth=opt.visdom.cam_depth)
        cam_ref = cam_ref.numpy()  # (N,10,3)
    # set up plot window(s)
    plt.title("epoch {}".format(ep))
    ax1 = fig.add_subplot(121, projection="3d")
    ax2 = fig.add_subplot(122, projection="3d")

    bound = 3

    setup_3D_plot(ax1, elev=-90, azim=-90, lim=edict(x=(-bound, bound), y=(-bound, bound), z=(-bound, bound)))  # x=(-1,1),y=(-1,1),z=(-1,1)
    setup_3D_plot(ax2, elev=0, azim=-90, lim=edict(x=(-bound, bound), y=(-bound, bound), z=(-bound, bound)))
    ax1.set_title("forward-facing view", pad=0)
    ax2.set_title("top-down view", pad=0)
    plt.subplots_adjust(left=0, right=1, bottom=0, top=0.95, wspace=0, hspace=0)
    plt.margins(tight=True, x=0, y=0)
    # plot the cameras
    N = len(cam)
    color = plt.get_cmap("gist_rainbow")
    for i in range(N):
        if pose_ref is not None:
            ax1.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(0.3,0.3,0.3),linewidth=1)
            ax2.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(0.3,0.3,0.3),linewidth=1)
            ax1.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(0.3,0.3,0.3),s=40)
            ax2.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(0.3,0.3,0.3),s=40)
        c = np.array(color(float(i)/N))*0.8
        ax1.plot(cam[i,:,0],cam[i,:,1],cam[i,:,2],color=c)
        ax2.plot(cam[i,:,0],cam[i,:,1],cam[i,:,2],color=c)
        ax1.scatter(cam[i,5,0],cam[i,5,1],cam[i,5,2],color=c,s=40)
        ax2.scatter(cam[i,5,0],cam[i,5,1],cam[i,5,2],color=c,s=40)

    #red and black
    # for i in range(N):
    #     if pose_ref is not None:
    #         ax1.plot(cam_ref[i, :, 0], cam_ref[i, :, 1], cam_ref[i, :, 2], color=(0.3, 0.3, 0.3), linewidth=1)
    #         ax2.plot(cam_ref[i, :, 0], cam_ref[i, :, 1], cam_ref[i, :, 2], color=(0.3, 0.3, 0.3), linewidth=1)
    #         ax1.scatter(cam_ref[i, 5, 0], cam_ref[i, 5, 1], cam_ref[i, 5, 2], color=(0.3, 0.3, 0.3), s=40)
    #         ax2.scatter(cam_ref[i, 5, 0], cam_ref[i, 5, 1], cam_ref[i, 5, 2], color=(0.3, 0.3, 0.3), s=40)
    #
    #     # c = np.array(color(float(i)/N))*0.8
    #     c = (1, 0, 0)
    #     ax1.plot(cam[i, :, 0], cam[i, :, 1], cam[i, :, 2], color=c)
    #     ax2.plot(cam[i, :, 0], cam[i, :, 1], cam[i, :, 2], color=c)
    #     ax1.scatter(cam[i, 5, 0], cam[i, 5, 1], cam[i, 5, 2], color=c, s=40)
    #     ax2.scatter(cam[i, 5, 0], cam[i, 5, 1], cam[i, 5, 2], color=c, s=40)




    png_fname = "{}/{}.png".format(path, ep)
    plt.savefig(png_fname, dpi=75)
    # clean up
    plt.clf()



def plot_save_poses_blender(opt,fig,pose,pose_ref=None,path=None,ep=None):
    # get the camera meshes
    _,_,cam = get_camera_mesh(pose,depth=opt.visdom.cam_depth)
    cam = cam.numpy()
    if pose_ref is not None:
        _,_,cam_ref = get_camera_mesh(pose_ref,depth=opt.visdom.cam_depth)
        cam_ref = cam_ref.numpy()
    # set up plot window(s)
    ax = fig.add_subplot(111,projection="3d")
    ax.set_title("epoch {}".format(ep),pad=0)

    x_max = np.max([np.max(cam_ref[:, 5, 0]), np.max(cam[:, 5, 0])]) + 0.1
    x_min = np.min([np.min(cam_ref[:, 5, 0]), np.min(cam[:, 5, 0])]) - 0.1
    y_max = np.max([np.max(cam_ref[:, 5, 1]), np.max(cam[:, 5, 1])]) + 0.1
    y_min = np.min([np.min(cam_ref[:, 5, 1]), np.min(cam[:, 5, 1])]) - 0.1
    z_max = np.max([np.max(cam_ref[:, 5, 2]), np.max(cam[:, 5, 2])]) + 0.05
    z_min = np.min([np.min(cam_ref[:, 5, 2]), np.min(cam[:, 5, 2])]) - 0.05

    setup_3D_plot(ax,elev=90,azim=100,lim=edict(x=(x_min, x_max), y=(y_min, y_max), z=(z_min, z_max)))
    plt.subplots_adjust(left=0,right=1,bottom=0,top=0.95,wspace=0,hspace=0)
    plt.margins(tight=True,x=0,y=0)
    # plot the cameras
    N = len(cam)
    # ref_color = (0.7,0.2,0.7)
    ref_color = (0.3, 0.3, 0.3)
    pred_color = (0.7,0.2,0.7)#(0,0.6,0.7)#BARF
    ax.add_collection3d(Poly3DCollection([v[:4] for v in cam_ref],alpha=0.2,facecolor=ref_color))
    for i in range(N):
        ax.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=ref_color,linewidth=0.5)
        ax.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=ref_color,s=20)
    if ep==0:
        png_fname = "{}/GT.png".format(path)
        plt.savefig(png_fname,dpi=75)
    ax.add_collection3d(Poly3DCollection([v[:4] for v in cam],alpha=0.2,facecolor=pred_color))
    for i in range(N):
        ax.plot(cam[i,:,0],cam[i,:,1],cam[i,:,2],color=pred_color,linewidth=1)
        ax.scatter(cam[i,5,0],cam[i,5,1],cam[i,5,2],color=pred_color,s=20)
    for i in range(N):
        ax.plot([cam[i,5,0],cam_ref[i,5,0]],
                [cam[i,5,1],cam_ref[i,5,1]],
                [cam[i,5,2],cam_ref[i,5,2]],color=(1,0,0),linewidth=3)
    png_fname = "{}/{}_3d.png".format(path,ep)
    plt.savefig(png_fname,dpi=75)
    # clean up
    plt.clf()

def plot_save_poses_for_oneNall(opt,fig,pose,pose_ref=None,path=None,ep=None):
    # get the camera meshes
    _,_,cam = get_camera_mesh(pose,depth=opt.visdom.cam_depth)
    cam = cam.numpy()
    if pose_ref is not None:
        _,_,cam_ref = get_camera_mesh(pose_ref,depth=opt.visdom.cam_depth)
        cam_ref = cam_ref.numpy()
    # set up plot window(s)
    plt.title("epoch {}".format(ep))
    ax1 = fig.add_subplot(121,projection="3d")
    ax2 = fig.add_subplot(122,projection="3d")
    setup_3D_plot(ax1,elev=-90,azim=-90,lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)))  #lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)) lim=edict(x=(-2,2),y=(-2,2),z=(-2,2))
    setup_3D_plot(ax2,elev=0,azim=-90,lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)))  #lim=edict(x=(-1,1),y=(-1,1),z=(-1,1))
    ax1.set_title("forward-facing view",pad=0)
    ax2.set_title("top-down view",pad=0)
    plt.subplots_adjust(left=0,right=1,bottom=0,top=0.95,wspace=0,hspace=0)
    plt.margins(tight=True,x=0,y=0)

    #TODO : camers size

    # plot the cameras
    N = len(pose_ref)
    color = plt.get_cmap("gist_rainbow")
    gray_color = 0.8
    for i in range(N):
        if pose_ref is not None:
            ax1.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(gray_color,gray_color,gray_color),linewidth=1)
            ax2.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(gray_color,gray_color,gray_color),linewidth=1)
            ax1.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(gray_color,gray_color,gray_color),s=40)
            ax2.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(gray_color,gray_color,gray_color),s=40)
    c = np.array(color(float(1) / N)) * 0.8
    ax1.plot(cam[0, :, 0], cam[0, :, 1], cam[0, :, 2], color=c)
    ax2.plot(cam[0, :, 0], cam[0, :, 1], cam[0, :, 2], color=c)
    ax1.scatter(cam[0, 5, 0], cam[0, 5, 1], cam[0, 5, 2], color=c, s=40)
    ax2.scatter(cam[0, 5, 0], cam[0, 5, 1], cam[0, 5, 2], color=c, s=40)
    png_fname = "{}/{}.png".format(path,ep)
    plt.savefig(png_fname,dpi=75)
    # clean up
    plt.clf()



def plot_save_poses_for_oneNall_optisync(fig,pose,pose_ref=None,path=None,ep=None):
    # get the camera meshes
    _,_,cam = get_camera_mesh(pose,depth=0.5)
    cam = cam.numpy()
    if pose_ref is not None:
        _,_,cam_ref = get_camera_mesh(pose_ref,depth=0.5)
        cam_ref = cam_ref.numpy()
    # set up plot window(s)
    plt.title("epoch {}".format(ep))
    ax1 = fig.add_subplot(121,projection="3d")
    ax2 = fig.add_subplot(122,projection="3d")
    setup_3D_plot(ax1,elev=-90,azim=-90,lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)))  #lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)) lim=edict(x=(-2,2),y=(-2,2),z=(-2,2))
    setup_3D_plot(ax2,elev=0,azim=-90,lim=edict(x=(-1,1),y=(-1,1),z=(-1,1)))  #lim=edict(x=(-1,1),y=(-1,1),z=(-1,1))
    ax1.set_title("forward-facing view",pad=0)
    ax2.set_title("top-down view",pad=0)
    plt.subplots_adjust(left=0,right=1,bottom=0,top=0.95,wspace=0,hspace=0)
    plt.margins(tight=True,x=0,y=0)

    #TODO : camers size

    # plot the cameras
    N = len(pose_ref)
    color = plt.get_cmap("gist_rainbow")
    gray_color = 0.8
    for i in range(N):
        if pose_ref is not None:
            ax1.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(gray_color,gray_color,gray_color),linewidth=1)
            ax2.plot(cam_ref[i,:,0],cam_ref[i,:,1],cam_ref[i,:,2],color=(gray_color,gray_color,gray_color),linewidth=1)
            ax1.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(gray_color,gray_color,gray_color),s=40)
            ax2.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=(gray_color,gray_color,gray_color),s=40)
    c = np.array(color(float(1) / N)) * 0.8
    ax1.plot(cam[0, :, 0], cam[0, :, 1], cam[0, :, 2], color=c)
    ax2.plot(cam[0, :, 0], cam[0, :, 1], cam[0, :, 2], color=c)
    ax1.scatter(cam[0, 5, 0], cam[0, 5, 1], cam[0, 5, 2], color=c, s=40)
    ax2.scatter(cam[0, 5, 0], cam[0, 5, 1], cam[0, 5, 2], color=c, s=40)
    png_fname = "{}/{}.png".format(path,ep)
    plt.savefig(png_fname,dpi=75)
    # clean up
    plt.clf()

# for novel_view test
def plot_save_novel_poses(fig,pose,pose_ref=None,path=None,ep=None): # pose = novel_view, pose_ref= rectangle_pose
    # get the camera meshes
    _,_,cam = get_camera_mesh(pose,depth=0.5)
    cam = cam.numpy()
    if pose_ref is not None:
        _,_,cam_ref = get_camera_mesh(pose_ref,depth=0.5)
        cam_ref = cam_ref.numpy()
    # set up plot window(s)
    ax = fig.add_subplot(111,projection="3d")
    ax.set_title(" {}".format(ep),pad=0)
    setup_3D_plot(ax,elev=10,azim=50,lim=edict(x=(-3.5,1),y=(-3.5,1),z=(-3,1))) #lim=edict(x=(-1,1),y=(-1,1),z=(-0.5,0.3)) lim=edict(x=(-3,3),y=(-3,3),z=(-3,2.4))
    plt.subplots_adjust(left=0,right=1,bottom=0,top=0.95,wspace=0,hspace=0)
    plt.margins(tight=True,x=0,y=0)
    # plot the cameras
    N = len(cam)
    ref_color = (0.7,0.2,0.7)
    pred_color = (0,0.6,0.7)
    ax.add_collection3d(Poly3DCollection([v[:4] for v in cam_ref],alpha=0.2,facecolor=ref_color))

    for i in range(len(cam_ref)):
        ax.plot(cam_ref[i, :, 0], cam_ref[i, :, 1], cam_ref[i, :, 2], color=ref_color, linewidth=0.5)
        ax.scatter(cam_ref[i,5,0],cam_ref[i,5,1],cam_ref[i,5,2],color=ref_color,s=20)

    png_fname = "{}/{}_GT.png".format(path,ep)
    plt.savefig(png_fname,dpi=75)
    ax.add_collection3d(Poly3DCollection([v[:4] for v in cam],alpha=0.2,facecolor=pred_color))
    for i in range(N):
        ax.plot(cam[i,:,0],cam[i,:,1],cam[i,:,2],color=pred_color,linewidth=1)
    for i in range(N):
        ax.scatter(cam[i,5,0],cam[i,5,1],cam[i,5,2],color=pred_color,s=20)
    for i in range(N):
        ax.plot(cam[i,5,0],
                cam[i,5,1],
                cam[i,5,2],color=(1,0,0),linewidth=3)
    for i in range(len(cam_ref)):
        ax.plot(cam_ref[i,5,0],
                cam_ref[i,5,1],
                cam_ref[i,5,2],color=(1,0,0),linewidth=3)
    png_fname = "{}/{}.png".format(path,ep)
    plt.savefig(png_fname,dpi=75)
    # clean up
    plt.clf()

def setup_3D_plot(ax,elev,azim,lim=None):
    ax.xaxis.set_pane_color((1.0,1.0,1.0,0.0))
    ax.yaxis.set_pane_color((1.0,1.0,1.0,0.0))
    ax.zaxis.set_pane_color((1.0,1.0,1.0,0.0))
    ax.xaxis._axinfo["grid"]["color"] = (0.9,0.9,0.9,1)
    ax.yaxis._axinfo["grid"]["color"] = (0.9,0.9,0.9,1)
    ax.zaxis._axinfo["grid"]["color"] = (0.9,0.9,0.9,1)
    ax.xaxis.set_tick_params(labelsize=8)
    ax.yaxis.set_tick_params(labelsize=8)
    ax.zaxis.set_tick_params(labelsize=8)
    ax.set_xlabel("X",fontsize=16)
    ax.set_ylabel("Y",fontsize=16)
    ax.set_zlabel("Z",fontsize=16)
    ax.set_xlim(lim.x[0],lim.x[1])
    ax.set_ylim(lim.y[0],lim.y[1])
    ax.set_zlim(lim.z[0],lim.z[1])
    ax.view_init(elev=elev,azim=azim)
