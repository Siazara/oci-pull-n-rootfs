#!/Library/Frameworks/Python.framework/Versions/3.11/bin/python3

import subprocess as sp 
import argparse
import json
import os
from fnmatch import fnmatch
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('image')
parser.add_argument('--tag', required=False, default='latest')
parser.add_argument('--hub', required=False, default='localhost:5000')
parser.add_argument('--repo', required=False, default='')

def pull(image_name, tag, hub, repo):
    save_dir = f"{image_name}_{tag}"
    if not os.path.isdir(save_dir):
        os.mkdir(save_dir)
    
    sp.run(["curl",
             "-X", "GET",
             "--header",
             "Accept: application/vnd.docker.distribution.manifest.v2+json",
             "-L", 
             f"{hub}/v2/{repo}{image_name}/manifests/{tag}",
             "-o", f"{save_dir}/manifest_v2.json"])
    
    f = open(f"{save_dir}/manifest_v2.json", 'r')
    manifest = json.load(f)
    f.close()
    os.remove(f"{save_dir}/manifest_v2.json")
    digest = manifest['config']['digest'][7:]
    
    sp.run(["curl",
           "-X", "GET",
           "-L", 
           f"{hub}/v2/{repo}{image_name}/blobs/sha256:{digest}", "-o",
           f"{save_dir}/{digest}.json"])
    
    layers = []
    for i in range(len(manifest['layers'])):
        digest = manifest['layers'][i]['digest']

        sp.run(["curl",
            "-X", "GET",
            "-L", 
            f"{hub}/v2/{repo}{image_name}/blobs/{digest}", "-o",
            f"{save_dir}/layer{i}.tar"])
        
        if not os.path.isdir(f"{save_dir}/layers"):
            os.mkdir(f"{save_dir}/layers")
                    
        if os.path.isdir(f"{save_dir}/layers/l{i}"):
            shutil.rmtree(f"{save_dir}/layers/l{i}")
        
        os.mkdir(f"{save_dir}/layers/l{i}")
        sp.run(["tar",
                "-xf",
                f"{save_dir}/layer{i}.tar",
                "-C",
                f"{save_dir}/layers/l{i}"])

        layers.append(f"layer{i}.tar")
    
    manifest_docker = {"Config": f"{manifest['config']['digest'][7:]}.json",
    "RepoTags": [f"{image_name}:{tag}"],
    "layers": f"{layers}"}
    with open(f'{save_dir}/manifest.json', 'w') as f: 
        json.dump(manifest_docker, f)
        
    return save_dir, manifest
    
def create_fs(save_dir, manifest):
    target_path = f"{save_dir}/layers/target"
    merged_path = f"{save_dir}/layers/merged"
    if os.path.isdir(merged_path):
        shutil.rmtree(merged_path)

    os.mkdir(merged_path)
    
    if os.path.isdir(target_path):
        shutil.rmtree(target_path)

    os.mkdir(target_path)
    
    lowerdir = ''
    for i in range(len(manifest['layers'])-1, 0, -1):
        lowerdir += f"{save_dir}/layers/l{i}:"
        
    lowerdir += f"{save_dir}/layers/l0"

    sp.run(["mount",
            "-t",
            "overlay",
            "overlay",
            f"-olowerdir={lowerdir}",
            merged_path])
    
    sp.run(["cp", "-a", merged_path + '/.', target_path])
    sp.run(["umount", merged_path])

    for path, subdirs, files in os.walk(target_path):
        for file in files:
            path_file = os.path.join(path, file)
            if fnmatch(file, "*.opq"):
                os.remove(path_file)
            
            elif fnmatch(file, ".wh.*"):
                if os.path.isdir(os.path.join(path, file[4:])):
                    shutil.rmtree(os.path.join(path, file[4:]))
                else:
                    os.remove(os.path.join(path, file[4:]))

                os.remove(os.path.join(path, file))

if __name__ == '__main__':
    args = parser.parse_args()
    image_name = args.image
    if args.repo != '':
        repo = args.repo + '/'
    else:
        repo = args.repo
    
    save_dir, manifest = pull(image_name, args.tag, args.hub, repo)
    create_fs(save_dir, manifest)
