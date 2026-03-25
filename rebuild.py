import os
import subprocess

def main():
    os.chdir('MCStructs')
    subprocess.run('git add .', shell=True, check=True)
    subprocess.run('git diff HEAD > ../patch.patch', shell=True, check=True)


if __name__ == '__main__':
    main()
