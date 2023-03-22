#!/bin/bash

# Declare variable for deploy path
DEPLOY_PATH="/var/www/pux-button"

# Copy specific files
cp log_config.py $DEPLOY_PATH
cp pux_button.py $DEPLOY_PATH
cp pux_job.sh $DEPLOY_PATH
rsync -av --ignore-missing-args resources/ $DEPLOY_PATH/resources/

# Generate list of dependencies from dev directory
pip freeze >$DEPLOY_PATH/requirements.txt

#Navigate to project directory
cd $DEPLOY_PATH

#Make pux_job.sh executable
chmod +x pux_job.sh

#Update dependencies
source venv/bin/activate
pip install -r requirements.txt
rm requirements.txt
rm -rf logs/*

# Check if job is already scheduled
job="/bin/bash $DEPLOY_PATH/pux_job.sh 2>> $DEPLOY_PATH/logs/pux_button_error.log"
if ! crontab -l | grep "$job"; then
  (crontab -l; echo "0 8 * * 1-5 $job") | crontab -
fi
