# viera - Deployment Manager
#### Version 2018-11-28

## Table of contents
* [Introduction](#introduction)
* [Objectives](#objectives)
* [Example: Solution Blueprint](#example-solution-blueprint)
* [Example: Deployment file](#example-deployment-file)
* [Architecture](#architecture)
* [How to write blueprint](#blueprint)

### Introduction

How to deploy service on Edge Computing platform is one challenge for customer of Edge Computing because diversity and complexity in edge environment. Like as cloud platform, you can manage your edge resource using an infrastructure-as-code approach. Treating your infrastructure as code involves defining your service through templates and configuration files and keep the files in a source code repository, even more, the template for one specific service can be in Edge Service marketplace. It will simplify user’s development and deployment experience for Edge computing. Given these requirements deployment manager was proposed for Verge9.

### Objectives

Deployment Manager will help customer to deploy end-to-end solution on Verge9. The major objectives will be followings:

- TOSES blueprint -> TOSES deployment file 
- Current Network Map (TOSEN) and Deployment State (TOSES) are also inputs 
- Downloadable and runnable locally as a separate module 
- Deployable as OpenFaaS function on Edge Devices (REST API interface)

### Example: Solution Blueprint

```yaml
Solution:
  name: Autodoor
  id: identity_for_the_solution
  description: open door by face recognition

  blocks:
    ip_camera:
      Type: device
      Class: nxp.camera.ip_camera
      status: init
      Properties:
        IP: 192.168.1.100
        format: H264
        resolution:  640x480
        protocol: rtsp
        user: xxxx
        pw: xxxxxxxx
        appendix: /h264/ch1/sub/av_stream
 
    DataStreamer:
      Type: service
      Class: apache.kafka
      Description: Message bus for AI data stream
      status: init
      Properties:
        Topics:
          T1:
            Name: data_send1
            Partition: 0
          T2:
            Name: data_send2
            Partition: 0
          T3:
            Name: data_send3
            Partition: 0
 
    VideoIngestion:
      Type: service
      Class: nxp.videoingestion
      Properties:
        Description:  Convert video to data streamer
        Hardware:
          CPU: 1G
          Mem: 1000M
          Space: 1G
        Source:
          Type: nxp.camera.ip_camera
          Name: ip_camera
        Target:
          Name: DataStreamer
          Type: apache.kafka
          Role: Producer
          Topic: DataStreamer.T1
  
    face_detection:
      Type: service
      Class: nxp.facedetection
      status: init
      Properties:
        Description:  Fetch video stream from data streamer, detect faces in the image, mark the position of faces, then send information to data streamer.
        Hardware:
          CPU: 1G
          Mem: 1000M
          Space: 1G
        Source:
          Type: apache.kafka
          Role: Consumer
          Topic: DataStreamer.T1
        Target:
          Type: apache.kafka
          Role: Producer
          Topic: DataStreamer.T2
 
    face_recognition:
      Type: service
      Class: nxp.facedetection
      status: init
      Properties:
        Description:  Fetch face information detected by face detection service from data streamer, recognise identity of face, then send to data streamer.
        Hardware:
          CPU: 1G
          Mem: 1000M
          Space: 1G
        Source:
          Type: apache.kafka
          Role: Consumer
          Topic: DataStreamer.T2
        Target:
          Type: apache.kafka
          Role: Producer
          Topic: DataStreamer.T3
  
    face_recognition_dashboard:
      Type: service
      Class: nxp.facerecognition_dashboard
      status: init
      Properties:
        Description:  Fetch face information detected by face detection service from data streamer, recognise identity of face, then send to data streamer.
        Hardware:
          CPU: 1G
          Mem: 1000M
          Space: 1G
        Source:
          Name: DataStreamer
          Type: apache.kafka
          Role: Consumer
          Topic: DataStreamer.T3
```
### Example: Deployment file
``` json
{
    "videodashboard-vd1": {
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
                    "name": "videodashboard-vd1", 
                    "image": "devops.nxp.com/videodashboard:1.3.2", 
                    "args": [
                        "python WebApp.py"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": {
                                "apache.kafka": {
                                    "topic": "data_send3", 
                                    "ip": "x.x.x.x", 
                                    "partition": 0, 
                                    "port": 9092
                                }
                            }
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "35d07fcae2d1538ebb5f8972e1ddc523.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "videodashboard-vd1"
            }, 
            "namespace": "default", 
            "name": "videodashboard-vd1"
        }
    }, 
    "facerecognition-fr1": {
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
                    "name": "facerecognition-fr1", 
                    "image": "devops.nxp.com/facerecognition:1.3.2", 
                    "args": [
                        "/bin/facerecognition"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": {
                                "source": {
                                    "apache.kafka": {
                                        "topic": "data_send2", 
                                        "ip": "x.x.x.x", 
                                        "partition": 0, 
                                        "port": 9092
                                    }
                                }, 
                                "target": {
                                    "apache.kafka": {
                                        "topic": "data_send3", 
                                        "ip": "10.192.208.124", 
                                        "partition": 0, 
                                        "port": 9092
                                    }
                                }
                            }
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "35d07fcae2d1538ebb5f8972e1ddc523.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "facerecognition-fr1"
            }, 
            "namespace": "default", 
            "name": "facerecognition-fr1"
        }
    }, 
    "videoingestion-vi1": {
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
                    "name": "videoingestion-vi1", 
                    "image": "devops.nxp.com/videoingestion:1.3.2", 
                    "args": [
                        "/bin/videoingestion"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": {
                                "nxp.camera.ip_camera": {
                                    "protocol": "rtsp", 
                                    "pw": "xxxxxxx", 
                                    "format": "H264", 
                                    "url": "rtsp://xxxx:xxxxxxx@10.11.10.1/h264/ch1/sub/av_stream", 
                                    "ip": "10.11.10.1", 
                                    "appendix": "/h264/ch1/sub/av_stream", 
                                    "user": "admin", 
                                    "resolution": "640x480"
                                }, 
                                "apache.kafka": {
                                    "topic": "data_send1", 
                                    "ip": "10.192.208.124", 
                                    "partition": 0, 
                                    "port": 9092
                                }
                            }
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "35d07fcae2d1538ebb5f8972e1ddc523.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "videoingestion-vi1"
            }, 
            "namespace": "default", 
            "name": "videoingestion-vi1"
        }
    }, 
    "kafka-stream1": {
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
                    "name": "kafka-stream1", 
                    "image": "devops.nxp.com/kafka:1.3.2", 
                    "args": [
                        "/bin/kafka"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": ""
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "35d07fcae2d1538ebb5f8972e1ddc523.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "kafka-stream1"
            }, 
            "namespace": "default", 
            "name": "kafka-stream1"
        }
    }, 
    "facedetection-fd1": {
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
                    "name": "facedetection-fd1", 
                    "image": "devops.nxp.com/facedetect:1.3.2", 
                    "args": [
                        "/bin/facedetection"
                    ], 
                    "command": [
                        "/bin/bash", 
                        "-c"
                    ], 
                    "env": [
                        {
                            "name": "SERVICE_PARAMETERS", 
                            "value": {
                                "source": {
                                    "apache.kafka": {
                                        "topic": "data_send1", 
                                        "ip": "x.x.x.x", 
                                        "partition": 0, 
                                        "port": 9092
                                    }
                                }, 
                                "target": {
                                    "apache.kafka": {
                                        "topic": "data_send2", 
                                        "ip": "x.x.x.x", 
                                        "partition": 0, 
                                        "port": 9092
                                    }
                                }
                            }
                        }
                    ], 
                    "imagePullPolicy": "IfNotPresent"
                }
            ], 
            "nodeSelector": {
                "kubernetes.io/hostname": "35d07fcae2d1538ebb5f8972e1ddc523.lsdk.generic.ls1046ardb.nxp"
            }
        }, 
        "apiVersion": "v1", 
        "metadata": {
            "labels": {
                "name": "facedetection-fd1"
            }, 
            "namespace": "default", 
            "name": "facedetection-fd1"
        }
    }
}
```
