# Door opener with realtime face detection

In recent years, facial recognition technology has become increasingly popular as a security measure for businesses and homes. Face recognition software can identify people from the live camera and automatically open doors. It's a great tool for security but can also be helpful in everyday life. For example, you can use it to open your door if you forget your key, or to let your dog out when you're away from home.

You need to know a few things before using facial recognition software. First, it needs a camera. Second, you need to train the software on a set of faces. Third, you need to keep the software up-to-date so that it can identify new faces. Finally, you need to be careful about who you allow access to the software. If someone unauthorized accesses your system, they could use it to invade your privacy or even hijack your camera.

## How does it work?

It captures frames from a camera and initially tries to detect faces, if it finds faces then it starts using computer vision to detect faces from a known face list. If its matches anyone known, it will open the door. The downside is that computer vision can't always detect faces in low-light or occluded situations, so it will sometimes default to not opening the door. The upside is that if it does find a face, it will be very confident in its match and open the door very quickly. The system is still in development, but it has been successful so far at recognizing people from security footage. We are currently working on making the system more robust so it can be used in more scenarios.

## Technical Details

It supports real time streaming camera(RTSP), http footage etc anything what opencv supports. This system uses dlib, so it's very hard to get it working in windows environment even we had a hard time to make it compatible with very latest version of python. So, the preffered to way use this system is using docker. No port openings are needed.

### Hardware requirements

* It has multiproccesing enabled. As it uses computer vision, it requires a good processor and multiple cores. (More than 2 cores above 2Ghz)
* Attendance machine from [ZKteco](https://www.zkteco.com/) brand (tested on K-51) with door lock installed.
* Any camera which you can pass to the environment variable.
