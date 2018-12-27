# viera - Deployment Manager
#### Version 2018-12-27

## Table of contents
* [Introduction](#introduction)
* [Objectives](#objectives)
* [Architecture](#architecture)
* [How to write blueprint](#blueprint)
* [Example: Solution Blueprint](#example-home-surveillance-system-blueprint)
* [Example: Deployment file](#example-deployment-file-for-home-surveillance-system)

### Introduction

How to deploy service on Edge Computing platform is one challenge for customer of Edge Computing because diversity and complexity in edge environment. Like as cloud platform, you can manage your edge resource using an infrastructure-as-code approach. Treating your infrastructure as code involves defining your service through templates and configuration files and keep the files in a source code repository, even more, the template for one specific service can be in Edge Service marketplace. It will simplify user’s development and deployment experience for Edge computing. Given these requirements deployment manager was proposed for Verge9.

### Objectives

Deployment Manager will help customer to deploy end-to-end solution on Verge9. The major objectives will be followings:

- TOSES blueprint -> TOSES deployment file 
- Current Network Map (TOSEN) and Deployment State (TOSES) are also inputs 
- Downloadable and runnable locally as a separate module 
- Deployable as OpenFaaS function on Edge Devices (REST API interface)

### Example: Home Surveillance System Blueprint

```yaml
Solution:
    name: smart_home
    id: a_random_alphabeit_string_generated_by_system
    version: v1
    blocks:
        camera-1:
            role: device
            type: VideoSource
            class: nxp.ipcamera
            encode: jpg
            # Empty means to query device from database
            deviceid: ""
        kafka-1:
            role: service
            type: Videostream
            class: apache.kafka
            service_port: 9092
            topics:
                Producer:
                    video-ingestion-1:
                        topic: ingest
                        partition_id: 0
                        group: group1
                    face-recognition-1:
                        topic: recognition
                        partition_id: 0
                        group: group3
                Consumer:
                    face-recognition-1:
                        topic: ingest
                        partition_id: 0
                        group: group2
            Compatability:
                arch: arm64
                os: linux
                rfs: ubuntu1604
            deviceid: 93c3dd5ff9b05c6e935325d8400252bf.lsdk.generic.ls2088ardb.nxp
        video-ingestion-1:
            role: service
            class: nxp.video_ingestion
            Source: camera-1
            Target: kafka-1
            Input:
                name: VideoSource
            Output:
                name: Videostream
            Compatability:
                arch: arm64
                os: linux
                rfs: ubuntu1604
            deviceid: a514aea576255934994e6794589784eb.iot.multimedia.imx8.nxp
        face-recognition-1:
            role: service
            class: nxp.face_recognition
            Source: kafka-1
            Target: kafka-1
            Input:
                name: Videostream
            Output:
                name: Videostream
            Compatability:
                arch: arm64
                os: linux
                rfs: ubuntu1604
            deviceid: ab8dc5794cda54378b80f8152f149ad5.lsdk.generic.ls1046ardb.nxp
```
### Example: Deployment file for Home Surveillance System
``` json
{
    "face-recognition-1": {
        "kind": "Pod", 
        "spec": {
            "restartPolicy": "Always", 
            "hostNetwork": true, 
            "imagePullSecrets": [
                {
                    "name": "secretnxp"
                }
            ], 
            "containers": [
                {
                    "securityContext": {
                        "privileged": true
                    }, 
                    "name": "face-recognition-1", 
                    "image": "devops.nxp.com/deploy_manage_facerecognize:v1.1", 
                    "args": [
                        "cd /root/test_new/ && python facerecognition.py"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": "{\"input\": {\"VideoSource\": {\"username\": null, \"encode\": null, \"StreamID\": null, \"url\": null, \"password\": null, \"Resolution\": null, \"Video format\": null}, \"Videostream\": {\"Broker_IP\": \"xxx.xxx.xxx.xxx\", \"TopicID\": \"ingest\", \"PartitionID\": 0, \"Broker_Port\": 9092, \"Group\": \"group2\"}, \"name\": \"Videostream\", \"Featuredb\": {\"DB_admin_username\": null, \"DB_name\": null, \"DB_address\": null, \"DB_admin_password\": null}}, \"output\": {\"Videostream\": {\"Broker_IP\": \"xxx.xxx.xxx.xxx\", \"TopicID\": \"recognition\", \"PartitionID\": 0, \"Broker_Port\": 9092, \"Group\": \"group3\"}, \"name\": \"Videostream\"}}"
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "ab8dc5794cda54378b80f8152f149ad5.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "face-recognition-1"
            }, 
            "namespace": "default", 
            "name": "face-recognition-1"
        }
    }, 
    "video-ingestion-1": {
        "kind": "Pod", 
        "spec": {
            "restartPolicy": "Always", 
            "hostNetwork": true, 
            "imagePullSecrets": [
                {
                    "name": "secretnxp"
                }
            ], 
            "containers": [
                {
                    "securityContext": {
                        "privileged": true
                    }, 
                    "name": "video-ingestion-1", 
                    "image": "devops.nxp.com/deploy_manage_ingestion_facedetect:v1.1", 
                    "args": [
                        "cd /home/root/ncnn-face-recon-imx8_m2/build/ && ./facedetect"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": "{\"input\": {\"VideoSource\": {\"username\": \"admin\", \"encode\": \"jpg\", \"StreamID\": \"rtsp\", \"url\": \"rtsp://admin:a12345678@192.168.xxx.xxx//h264/ch1/sub/av_stream\", \"password\": \"a12345678\", \"Resolution\": \"640x480\", \"Video format\": \"H264\"}, \"Videostream\": {\"Broker_IP\": null, \"TopicID\": null, \"PartitionID\": null, \"Broker_Port\": null, \"Group\": null}, \"name\": \"VideoSource\", \"Featuredb\": {\"DB_admin_username\": null, \"DB_name\": null, \"DB_address\": null, \"DB_admin_password\": null}}, \"output\": {\"Videostream\": {\"Broker_IP\": \"xxx.xxx.xxx.xxx\", \"TopicID\": \"ingest\", \"PartitionID\": 0, \"Broker_Port\": 9092, \"Group\": \"group1\"}, \"name\": \"Videostream\"}}"
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "a514aea576255934994e6794589784eb.iot.multimedia.imx8.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "video-ingestion-1"
            }, 
            "namespace": "default", 
            "name": "video-ingestion-1"
        }
    }, 
    "kafka-1": {
        "kind": "Pod", 
        "spec": {
            "restartPolicy": "Always", 
            "hostNetwork": true, 
            "imagePullSecrets": [
                {
                    "name": "secretnxp"
                }
            ], 
            "containers": [
                {
                    "securityContext": {
                        "privileged": true
                    }, 
                    "name": "kafka-1", 
                    "image": "devops.nxp.com/kafka:broker", 
                    "args": [
                        "cd ~/kafka/zookeeper-3.4.13 && bin/zkServer.sh start conf/zoo.cfg && sleep 10 && cd ~/kafka/kafka_2.11-2.0.0 && bin/kafka-server-start.sh  config/server.properties &"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "PATH", 
                            "value": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/jdk/jdk1.8.0_181/bin"
                        }, 
                        {
                            "name": "JAVA_HOME", 
                            "value": "/usr/jdk/jdk1.8.0_181"
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "93c3dd5ff9b05c6e935325d8400252bf.lsdk.generic.ls2088ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "kafka-1"
            }, 
            "namespace": "default", 
            "name": "kafka-1"
        }
    }
}
```
