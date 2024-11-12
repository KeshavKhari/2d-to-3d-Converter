import cv2 as cv
import numpy as np
import torch
from PIL import Image
import open3d as o3d
from transformers import GLPNImageProcessor, GLPNForDepthEstimation

# Load the model and processor
feature_extractor = GLPNImageProcessor.from_pretrained("vinvino02/glpn-nyu")
model = GLPNForDepthEstimation.from_pretrained("vinvino02/glpn-nyu")

# Image processing function
def process_image(image_path):
    # Read the original image
    img = cv.imread(image_path)

    denoised_img = cv.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    image = Image.fromarray(cv.cvtColor(denoised_img, cv.COLOR_BGR2RGB))

    new_height = 480 if image.height > 480 else image.height
    new_height -= (new_height % 32)

    new_width = int(new_height * image.width / image.height)

    diff = new_width % 32

    new_width = new_width - diff if diff < 16 else new_width + 32 - diff

    new_size = (new_width, new_height)
    image = image.resize(new_size)

    # Feature extraction
    inputs = feature_extractor(images=image, return_tensors="pt")

    # Run the model
    with torch.no_grad():
        outputs = model(**inputs)
        predicted_depth = outputs.predicted_depth

    pad = 16
    output = predicted_depth.squeeze().cpu().numpy() * 1000.0

    output = output[pad: -pad, pad:-pad]

    image = image.crop((pad, pad, image.width - pad, image.height - pad))

    # Convert depth to image
    depth_image = (output * 255 / np.max(output)).astype("uint8")
    image = np.array(image)

    # Create depth and RGB images for Open3D
    depth_o3d = o3d.geometry.Image(depth_image)
    image_o3d = o3d.geometry.Image(image)
    rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(image_o3d, depth_o3d, convert_rgb_to_intensity=False)

    # Camera intrinsics
    width, height = image.shape[1], image.shape[0]
    camera_intrinsic = o3d.camera.PinholeCameraIntrinsic()
    camera_intrinsic.set_intrinsics(width, height, 500, 500, width / 2, height / 2)

    # Create point cloud
    pcd_raw = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, camera_intrinsic)

    # Post-process the 3D point cloud
    cl, ind = pcd_raw.remove_statistical_outlier(nb_neighbors=20, std_ratio=6.0, print_progress=False)
    pcd = pcd_raw.select_by_index(ind)

    # Estimate normals and orient them
    pcd.estimate_normals()
    pcd.orient_normals_to_align_with_direction()

    # Surface reconstruction using Poisson
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=10, n_threads=1)[0]

    # Rotate the mesh
    rotation = mesh.get_rotation_matrix_from_xyz((np.pi, 0, 0))
    mesh.rotate(rotation, center=(0, 0, 0))

    # Save mesh or depth image
    mesh_file = "images/mesh.ply"
    o3d.io.write_triangle_mesh(mesh_file, mesh)

    return mesh_file  # or you can return the processed image if you prefer
