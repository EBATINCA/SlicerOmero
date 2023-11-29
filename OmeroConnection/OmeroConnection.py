import logging
import os
import qt
from typing import Annotated, Optional

from omero.gateway import BlitzGateway


import vtk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode


#
# OmeroConnection
#

class OmeroConnection(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("OmeroConnection")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Csaba Pinter (EBATINCA. S.L)", "Idafen Santana (EBATINCA. S.L)"]
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""This module has been
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Csaba Pinter and Idafen Santana (EBATINCA. S.L). The work was funded by the
CECAD Imaging Facility at the University of Cologne as part of the NFDI4Bioimage consortium.
""")



#
# OmeroConnectionParameterNode
#

#TODO: This class is not used in this module.
@parameterNodeWrapper
class OmeroConnectionParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """
    inputVolume: vtkMRMLScalarVolumeNode
    imageThreshold: Annotated[float, WithinRange(-100, 500)] = 100
    invertThreshold: bool = False
    thresholdedVolume: vtkMRMLScalarVolumeNode
    invertedVolume: vtkMRMLScalarVolumeNode


#
# OmeroConnectionWidget
#

class OmeroConnectionWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/OmeroConnection.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = OmeroConnectionLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Input fields
        self.ui.hostLineEdit.textEdited.connect(self.updateFromGUI)
        self.ui.portLineEdit.textEdited.connect(self.updateFromGUI)
        self.ui.userNameLineEdit.textEdited.connect(self.updateFromGUI)
        self.ui.passwordLineEdit.textEdited.connect(self.updateFromGUI)

        # Buttons
        self.ui.testConnectionButton.clicked.connect(self.onTestConnectionButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

        # Input fields
        self.ui.hostLineEdit.textEdited.disconnect()
        self.ui.portLineEdit.textEdited.disconnect()
        self.ui.userNameLineEdit.textEdited.disconnect()
        self.ui.passwordLineEdit.textEdited.disconnect()

    def enter(self) -> None:
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

        # Fill connection information from configuration
        settings = qt.QSettings()

        self.ui.hostLineEdit.text = settings.value('Omero/Host')
        self.ui.portLineEdit.text = settings.value('Omero/Port')
        self.ui.userNameLineEdit.text = settings.value('Omero/Username')
        self.ui.passwordLineEdit.text = settings.value('Omero/Password')

        self._checkCanApply()

    def exit(self) -> None:
        """
        Called each time the user opens a different module.
        """
        pass
        # # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        # if self._parameterNode:
        #     self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
        #     self._parameterNodeGuiTag = None
        #     self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        # if not self._parameterNode.inputVolume:
        #     firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        #     if firstVolumeNode:
        #         self._parameterNode.inputVolume = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[OmeroConnectionParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        pass  #TODO: We do not use the parameter node in this module (only configuration)
        # if self._parameterNode:
        #     self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
        #     self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        # self._parameterNode = inputParameterNode
        # if self._parameterNode:
        #     # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
        #     # ui element that needs connection.
        #     self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
        #     self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        #     self._checkCanApply()

    def updateFromGUI(self):
        """
        Update configuration based on the input fields.
        """
        settings = qt.QSettings()
        settings.setValue('Omero/Host', self.ui.hostLineEdit.text)
        settings.setValue('Omero/Port', self.ui.portLineEdit.text)
        settings.setValue('Omero/Username', self.ui.userNameLineEdit.text)
        settings.setValue('Omero/Password', self.ui.passwordLineEdit.text)

        self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        settings = qt.QSettings()
        host = settings.value('Omero/Host')
        port = settings.value('Omero/Port')
        username = settings.value('Omero/Username')
        password = settings.value('Omero/Password')
        if host and port and username and password:
            self.ui.testConnectionButton.toolTip = _("Check OMERO connection")
            self.ui.testConnectionButton.enabled = True
        else:
            self.ui.testConnectionButton.toolTip = _("Need to fill connection information")
            self.ui.testConnectionButton.enabled = False

    def onTestConnectionButton(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        with slicer.util.tryWithErrorDisplay(_("Failed to connect to OMERO server."), waitCursor=True):
            settings = qt.QSettings()
            host = settings.value('Omero/Host')
            port = settings.value('Omero/Port')
            username = settings.value('Omero/Username')
            password = settings.value('Omero/Password')

            # Idafen: addded connection test
            try:
                conn = BlitzGateway(username, password, host, port)
                conn.connect()
                conn.close()
                slicer.util.infoDisplay(f'Connection to OMERO server was successful.')
            except Exception as e:
                slicer.util.errorDisplay(f'Connection to OMERO server failed: {str(e)}')


#
# OmeroConnectionLogic
#

class OmeroConnectionLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return OmeroConnectionParameterNode(super().getParameterNode())

    def scanFileSystemForImage(self):
        pass  #TODO:

    def loadImageFromFile(self, filePath):
        pass  #TODO:

    # def process(self,
    #             inputVolume: vtkMRMLScalarVolumeNode,
    #             outputVolume: vtkMRMLScalarVolumeNode,
    #             imageThreshold: float,
    #             invert: bool = False,
    #             showResult: bool = True) -> None:
    #     """
    #     Run the processing algorithm.
    #     Can be used without GUI widget.
    #     :param inputVolume: volume to be thresholded
    #     :param outputVolume: thresholding result
    #     :param imageThreshold: values above/below this threshold will be set to 0
    #     :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    #     :param showResult: show output volume in slice viewers
    #     """

    #     if not inputVolume or not outputVolume:
    #         raise ValueError("Input or output volume is invalid")

    #     import time
    #     startTime = time.time()
    #     logging.info('Processing started')

    #     # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    #     cliParams = {
    #         'InputVolume': inputVolume.GetID(),
    #         'OutputVolume': outputVolume.GetID(),
    #         'ThresholdValue': imageThreshold,
    #         'ThresholdType': 'Above' if invert else 'Below'
    #     }
    #     cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    #     # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    #     slicer.mrmlScene.RemoveNode(cliNode)

    #     stopTime = time.time()
    #     logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')


#
# OmeroConnectionTest
#

class OmeroConnectionTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_OmeroConnection1()

    def test_OmeroConnection1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        self.delayDisplay('Test passed')
