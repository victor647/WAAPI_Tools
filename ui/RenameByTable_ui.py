# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'RenameByTable.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_RenameByTable(object):
    def setupUi(self, RenameByTable):
        if not RenameByTable.objectName():
            RenameByTable.setObjectName(u"RenameByTable")
        RenameByTable.resize(640, 480)
        self.verticalLayout = QVBoxLayout(RenameByTable)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lblObjectType = QLabel(RenameByTable)
        self.lblObjectType.setObjectName(u"lblObjectType")
        self.lblObjectType.setMaximumSize(QSize(60, 16777215))

        self.horizontalLayout.addWidget(self.lblObjectType)

        self.cbbObjectType = QComboBox(RenameByTable)
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.addItem("")
        self.cbbObjectType.setObjectName(u"cbbObjectType")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbbObjectType.sizePolicy().hasHeightForWidth())
        self.cbbObjectType.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.cbbObjectType)

        self.cbxExactMatch = QCheckBox(RenameByTable)
        self.cbxExactMatch.setObjectName(u"cbxExactMatch")
        self.cbxExactMatch.setChecked(True)

        self.horizontalLayout.addWidget(self.cbxExactMatch)

        self.cbxHasHeaderRow = QCheckBox(RenameByTable)
        self.cbxHasHeaderRow.setObjectName(u"cbxHasHeaderRow")
        self.cbxHasHeaderRow.setChecked(True)

        self.horizontalLayout.addWidget(self.cbxHasHeaderRow)

        self.btnChooseConfig = QPushButton(RenameByTable)
        self.btnChooseConfig.setObjectName(u"btnChooseConfig")

        self.horizontalLayout.addWidget(self.btnChooseConfig)

        self.btnDoRename = QPushButton(RenameByTable)
        self.btnDoRename.setObjectName(u"btnDoRename")

        self.horizontalLayout.addWidget(self.btnDoRename)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tblConfigItems = QTableWidget(RenameByTable)
        if (self.tblConfigItems.columnCount() < 3):
            self.tblConfigItems.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblConfigItems.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblConfigItems.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblConfigItems.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.tblConfigItems.setObjectName(u"tblConfigItems")
        self.tblConfigItems.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalLayout.addWidget(self.tblConfigItems)


        self.retranslateUi(RenameByTable)

        self.cbbObjectType.setCurrentIndex(5)


        QMetaObject.connectSlotsByName(RenameByTable)
    # setupUi

    def retranslateUi(self, RenameByTable):
        RenameByTable.setWindowTitle(QCoreApplication.translate("RenameByTable", u"\u8bfb\u8868\u6279\u91cf\u91cd\u547d\u540d", None))
        self.lblObjectType.setText(QCoreApplication.translate("RenameByTable", u"\u67e5\u627e\u7c7b\u578b", None))
        self.cbbObjectType.setItemText(0, QCoreApplication.translate("RenameByTable", u"ActorMixer", None))
        self.cbbObjectType.setItemText(1, QCoreApplication.translate("RenameByTable", u"AudioFileSource", None))
        self.cbbObjectType.setItemText(2, QCoreApplication.translate("RenameByTable", u"AuxBus", None))
        self.cbbObjectType.setItemText(3, QCoreApplication.translate("RenameByTable", u"BlendContainer", None))
        self.cbbObjectType.setItemText(4, QCoreApplication.translate("RenameByTable", u"Bus", None))
        self.cbbObjectType.setItemText(5, QCoreApplication.translate("RenameByTable", u"Event", None))
        self.cbbObjectType.setItemText(6, QCoreApplication.translate("RenameByTable", u"Folder", None))
        self.cbbObjectType.setItemText(7, QCoreApplication.translate("RenameByTable", u"GameParameter", None))
        self.cbbObjectType.setItemText(8, QCoreApplication.translate("RenameByTable", u"MusicPlaylistContainer", None))
        self.cbbObjectType.setItemText(9, QCoreApplication.translate("RenameByTable", u"MusicSegment", None))
        self.cbbObjectType.setItemText(10, QCoreApplication.translate("RenameByTable", u"MusicSwitchContainer", None))
        self.cbbObjectType.setItemText(11, QCoreApplication.translate("RenameByTable", u"MusicTrack", None))
        self.cbbObjectType.setItemText(12, QCoreApplication.translate("RenameByTable", u"RandomSequenceContainer", None))
        self.cbbObjectType.setItemText(13, QCoreApplication.translate("RenameByTable", u"Sound", None))
        self.cbbObjectType.setItemText(14, QCoreApplication.translate("RenameByTable", u"SoundBank", None))
        self.cbbObjectType.setItemText(15, QCoreApplication.translate("RenameByTable", u"State", None))
        self.cbbObjectType.setItemText(16, QCoreApplication.translate("RenameByTable", u"Switch", None))
        self.cbbObjectType.setItemText(17, QCoreApplication.translate("RenameByTable", u"SwitchContainer", None))
        self.cbbObjectType.setItemText(18, QCoreApplication.translate("RenameByTable", u"WorkUnit", None))

        self.cbxExactMatch.setText(QCoreApplication.translate("RenameByTable", u"\u5168\u5b57\u5339\u914d", None))
        self.cbxHasHeaderRow.setText(QCoreApplication.translate("RenameByTable", u"CSV\u5e26\u6709\u8868\u5934\u884c", None))
        self.btnChooseConfig.setText(QCoreApplication.translate("RenameByTable", u"\u8bfb\u53d6CSV\u6587\u4ef6", None))
        self.btnDoRename.setText(QCoreApplication.translate("RenameByTable", u"\u8fdb\u884c\u91cd\u547d\u540d", None))
        ___qtablewidgetitem = self.tblConfigItems.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("RenameByTable", u"\u539f\u547d\u540d", None));
        ___qtablewidgetitem1 = self.tblConfigItems.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("RenameByTable", u"\u65b0\u547d\u540d", None));
        ___qtablewidgetitem2 = self.tblConfigItems.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("RenameByTable", u"\u5f53\u524d\u72b6\u6001", None));
    # retranslateUi

