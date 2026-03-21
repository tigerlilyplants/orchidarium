import QtQuick
import QtQuick.Window

Window {
    // These are the dimensions of a RPi touch screen 2.
    width: 720
    height: 1280
    visible: true
    // We toggle the fullscreen option based on whether or not it's deployed on the pi as a wrapped process under a parent Python process, or
    // visibility: Window.FullScreen
    title: qsTr("Hello World")
}
