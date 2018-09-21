#!/usr/bin/python
#Import required modules
from __future__ import print_function
from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
import sys
from types import *
import logging

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import Draw
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

#The Viewer Class
class MolWidget(QtSvg.QSvgWidget):
    def __init__(self, mol = None, parent=None):
        #Also init the super class
        super(MolWidget, self).__init__(parent)

        #logging
        logging.basicConfig()
        self.logger = logging.getLogger()
        self.loglevel = logging.WARNING

        #This sets the window to delete itself when its closed, so it doesn't keep lingering in the background
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        #Private Properties
        self._mol = None #The molecule
        self._drawmol = None #Molecule for drawing
        self.drawer = None #drawing object for producing SVG
        self._selectedAtoms = [] #List of selected atoms

        #Bind signales to slots for automatic actions
        self.molChanged.connect(self.sanitize_draw)
        self.selectionChanged.connect(self.draw)

        #Initialize class with the mol passed
        self.mol = mol


    ##Properties and their wrappers
    @property
    def loglevel(self):
        return self.logger.level

    @loglevel.setter
    def loglevel(self, loglvl):
        self.logger.setLevel(loglvl)




    #Getter and setter for mol
    molChanged = QtCore.Signal(name="molChanged")
    @property
    def mol(self):
        return self._mol

    @mol.setter
    def mol(self, mol):
        if mol == None:
            mol=Chem.MolFromSmiles('')
        if mol != self._mol:
            #TODO assert that this is a RDKit mol
            if self._mol != None:
                self._prevmol = Chem.Mol(self._mol.ToBinary()) #Copy
            self._mol = mol
            self.molChanged.emit()

    def setMol(self, mol):
        self.mol = mol

    #Handling of selections
    selectionChanged = QtCore.Signal(name="selectionChanged")
    def selectAtomAdd(self, atomidx):
        if not atomidx in self._selectedAtoms:
            self._selectedAtoms.append(atomidx)
            self.selectionChanged.emit()

    def selectAtom(self, atomidx):
        self._selectedAtoms = [atomidx]
        self.selectionChanged.emit()

    def unselectAtom(self, atomidx):
        self.selectedAtoms.remove(atomidx)
        self.selectionChanged.emit()

    def clearAtomSelection(self):
        if self._selectedAtoms != []:
            self._selectedAtoms = []
            self.selectionChanged.emit()

    @property
    def selectedAtoms(self):
        return self._selectedAtoms

    @selectedAtoms.setter
    def selectedAtoms(self, atomlist):
        if atomlist != self._selectedAtoms:
            assert type(atomlist) == list, "selectedAtoms should be a list of integers"
            assert all(isinstance(item, int) for item in atomlist), "selectedAtoms should be a list of integers"
            self._selectedAtoms = atomlist
            self.selectionChanged.emit()

    def setSelectedAtoms(self, atomlist):
        self.selectedAtoms = atomlist

    #Actions and functions
    @QtCore.Slot()
    def draw(self):
        svg = self.getMolSvg()
        self.load(QtCore.QByteArray(svg.encode('utf-8')))

    @QtCore.Slot()
    def sanitize_draw(self):
        self.sanitizeMol()
        self.draw()

    sanitizeSignal = QtCore.Signal(str, name="sanitizeSignal")
    @QtCore.Slot()
    def sanitizeMol(self, kekulize=False):
        self._drawmol = Chem.Mol(self._mol.ToBinary()) #Is this necessary?
        try:
            Chem.SanitizeMol(self._drawmol)
            self.sanitizeSignal.emit("Sanitizable")
        except:
            self.sanitizeSignal.emit("UNSANITIZABLE")
            self.logger.warning("Unsanitizable")
            try:
                self._drawmol.UpdatePropertyCache(strict=False)
            except:
                self.sanitizeSignal.emit("UpdatePropertyCache FAIL")
                self.logger.error("Update Property Cache failed")
        #Kekulize
        if kekulize:
            try:
                Chem.Kekulize(self._drawmol)
            except:
                self.logger.warning("Unkekulizable")

        try:
            self._drawmol = rdMolDraw2D.PrepareMolForDrawing(self._drawmol, kekulize=kekulize)
        except ValueError:  # <- can happen on a kekulization failure
            self._drawmol = rdMolDraw2D.PrepareMolForDrawing(self._drawmol, kekulize=False)

        #Generate 2D coords if none present
        if not self._drawmol.GetNumConformers():
            rdDepictor.Compute2DCoords(self._drawmol)
            self.logger.debug("No Conformers found, computing 2D coords")
        else: #TODO match to already drawed
            self.logger.debug("%i Conformers in molecule"%self._drawmol.GetNumConformers())
#            try:
#                rdDepictor.GenerateDepictionMatching2DStructure(self._drawmol, self._prevmol)#, acceptFailure=True)
#            except:
            rdDepictor.Compute2DCoords(self._drawmol)


    finishedDrawing = QtCore.Signal(name="finishedDrawing")
    def getMolSvg(self):
        self.drawer = rdMolDraw2D.MolDraw2DSVG(300,300)
        #TODO, what if self._drawmol doesn't exist?
        if self._drawmol != None:
            #Chiral tags on R/S
            chiraltags = Chem.FindMolChiralCenters(self._drawmol)
            opts = self.drawer.drawOptions()
            for tag in chiraltags:
                idx = tag[0]
                opts.atomLabels[idx]= self._drawmol.GetAtomWithIdx(idx).GetSymbol() + ':' + tag[1]
            if len(self._selectedAtoms) > 0:
                colors={self._selectedAtoms[-1]:(1,0.2,0.2)} #Color lastly selected a different color
                self.drawer.DrawMolecule(self._drawmol, highlightAtoms=self._selectedAtoms, highlightAtomColors=colors)
            else:
                self.drawer.DrawMolecule(self._drawmol)
        self.drawer.FinishDrawing()
        self.finishedDrawing.emit()#Signal that drawer has finished
        svg = self.drawer.GetDrawingText().replace('svg:','')
        return svg


if __name__ == "__main__":
#    model = SDmodel()
#    model.loadSDfile('dhfr_3d.sd')
    mol = Chem.MolFromSmiles('CCN(C)c1ccccc1S')
    #rdDepictor.Compute2DCoords(mol)
    myApp = QtWidgets.QApplication(sys.argv)
    molview = MolWidget(mol)
    molview.selectAtom(1)
    molview.selectedAtoms = [1,2,3]
    molview.show()
    myApp.exec_()



