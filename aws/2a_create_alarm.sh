#!/bin/bash

echo "==========================================="
echo "     AWS CloudWatch CPU Alarm Creator"
echo "==========================================="
echo

echo "Available EC2 Instances:"
aws ec2 describe-instances \
--query "Reservations[].Instances[].[InstanceId,Tags[?Key=='Name'].Value|[0],State.Name]" \
--output table

echo
read -p "Enter EC2 Instance ID: " INSTANCE_ID

read -p "Enter Alarm Name: " ALARM_NAME

read -p "CPU Threshold (%): " THRESHOLD

read -p "Evaluation Periods (Default 2): " EVAL

if [ -z "$EVAL" ]; then
    EVAL=2
fi

read -p "Period in Seconds (Default 60): " PERIOD

if [ -z "$PERIOD" ]; then
    PERIOD=60
fi

echo
echo "Creating CloudWatch Alarm..."
echo

aws cloudwatch put-metric-alarm \
    --alarm-name "$ALARM_NAME" \
    --alarm-description "CPU exceeds ${THRESHOLD}% on ${INSTANCE_ID}" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period $PERIOD \
    --threshold $THRESHOLD \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods $EVAL \
    --dimensions Name=InstanceId,Value=$INSTANCE_ID \
    --unit Percent

if [ $? -eq 0 ]; then
    echo
    echo "==========================================="
    echo " Alarm Created Successfully"
    echo "==========================================="
    echo "Alarm Name     : $ALARM_NAME"
    echo "Instance ID    : $INSTANCE_ID"
    echo "CPU Threshold  : ${THRESHOLD}%"
    echo "Period         : ${PERIOD} sec"
    echo "Evaluation     : $EVAL"
else
    echo
    echo "Failed to create alarm."
fi
