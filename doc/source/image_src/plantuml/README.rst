plantuml
========


To build an image from a source file, you have to upload the plantuml JAR file
available on  http://plantuml.com/download.html.
After, just run this command to build your image:

.. code-block:: shell

    $ cd doc/source/images
    $ java -jar /path/to/plantuml.jar doc/source/image_src/plantuml/my_image.txt
    $ ls doc/source/images/
    my_image.png
