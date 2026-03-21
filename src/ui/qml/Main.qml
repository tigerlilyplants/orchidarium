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

    Connections {
        target: config
        function onRelayNamesChanged() {
            relayRepeater.model = 0
            relayRepeater.model = config.relayCount
        }
    }

    Popup {
        id: renamePopup
        modal: true
        focus: true
        anchors.centerIn: parent
        width: 300
        height: 180

        property int relayIndex: -1

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Text {
                text: "Rename Relay"
                font.pixelSize: 18
                font.bold: true
            }

            TextField {
                id: nameInput
                placeholderText: "Enter name"
            }

            Row {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter

                Button {
                    text: "Cancel"
                    onClicked: renamePopup.close()
                }

                Button {
                    text: "Save"
                    onClicked: {
                        if (renamePopup.relayIndex >= 0) {
                            config.setRelayName(renamePopup.relayIndex, nameInput.text)
                        }
                        nameInput.focus = false
                        renamePopup.close()
                    }
                }
            }
        }

        onOpened: {
            nameInput.text = config.relayName(relayIndex)
            nameInput.selectAll()
            nameInput.forceActiveFocus()
        }
    }

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
            id: relayRepeater
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

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            renamePopup.relayIndex = index
                            renamePopup.open()
                        }
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        Item { height: 1; width: 1 }

                        Text {
                            width: parent.width
                            height: (parent.height - 6) / 2
                            text: config.relayName(index)
                            color: "white"
                            font.bold: true
                            font.pixelSize: 22
                            minimumPixelSize: 6
                            fontSizeMode: Text.Fit
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.NoWrap
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            height: (parent.height - 6) / 2
                            text: relayStates[index].toUpperCase()
                            color: "white"
                            font.bold: true
                            font.pixelSize: 28
                            minimumPixelSize: 6
                            fontSizeMode: Text.Fit
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.NoWrap
                            elide: Text.ElideRight
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