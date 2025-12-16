DIR_NAME=$(basename "$PWD")

tmux new-session -d -s $DIR_NAME './launch.sh ; bash'