import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Window {
    width: 720
    height: 1280
    visible: true
    title: qsTr("Hello World")

    property var defaultConfig: ({
        fullscreen: false,
        relayCount: 4
    })

    readonly property bool fullscreenEnabled: config ? config.fullscreen : defaultConfig.fullscreen
    readonly property int relayCount: config ? config.relayCount : defaultConfig.relayCount

    visibility: fullscreenEnabled ? Window.FullScreen : Window.Windowed

    property var relayStates: Array(relayCount).fill("auto")

    function setRelayState(i, state) {
        let updated = relayStates.slice()
        updated[i] = state
        relayStates = updated
    }

    function sliderValueForState(state) {
        if (state === "on") return 0
        if (state === "auto") return 1
        return 2
    }

    function stateForSliderValue(value) {
        if (value < 0.5) return "on"
        if (value < 1.5) return "auto"
        return "off"
    }

    Row {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 10

        Repeater {
            model: config.relayCount

            delegate: Column {
                required property int index
                width: (parent.width - ((config.relayCount - 1) * 10)) / config.relayCount
                spacing: 16

                Rectangle {
                    width: parent.width
                    height: 120
                    radius: 12

                    color: relayStates[index] === "on" ? "#4CAF50"
                         : relayStates[index] === "off" ? "#F44336"
                         : "#9E9E9E"

                    border.color: "#333333"
                    border.width: 2

                    Column {
                        anchors.centerIn: parent
                        spacing: 8

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Relay " + (index + 1)
                            color: "white"
                            font.pixelSize: 20
                            font.bold: true
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: relayStates[index].toUpperCase()
                            color: "white"
                            font.pixelSize: 18
                            font.bold: true
                        }
                    }
                }

                Slider {
                    width: parent.width
                    from: 0
                    to: 2
                    stepSize: 1
                    snapMode: Slider.SnapAlways
                    value: sliderValueForState(relayStates[index])

                    onMoved: setRelayState(index, stateForSliderValue(value))
                    onValueChanged: setRelayState(index, stateForSliderValue(value))
                }

                Row {
                    width: parent.width

                    Text {
                        text: "ON"
                        width: parent.width / 3
                        horizontalAlignment: Text.AlignLeft
                        color: "#333333"
                        font.pixelSize: 9
                        font.bold: true
                    }

                    Text {
                        text: "AUTO"
                        width: parent.width / 3
                        horizontalAlignment: Text.AlignHCenter
                        color: "#333333"
                        font.pixelSize: 9
                        font.bold: true
                    }

                    Text {
                        text: "OFF"
                        width: parent.width / 3
                        horizontalAlignment: Text.AlignRight
                        color: "#333333"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }
        }
    }
}