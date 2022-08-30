mkdir victim-models
mkdir --parents training/emcts1-v2/cp127-vis512-warmstart-vis32
wget --directory-prefix=victim-models/ https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz
sudo usermod -aG docker $USER
sudo service docker start
ssh-keygen -t ed25519 -C "tom.hm.tseng@gmail.com"
cat /home/t/.ssh/id_ed25519.pub
sudo apt install python3-pip
pip3 install gpustat