# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'TemplateReplacer.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_TemplateReplacer(object):
    def setupUi(self, TemplateReplacer):
        if not TemplateReplacer.objectName():
            TemplateReplacer.setObjectName(u"TemplateReplacer")
        TemplateReplacer.resize(251, 143)
        self.verticalLayout = QVBoxLayout(TemplateReplacer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lblFindText = QLabel(TemplateReplacer)
        self.lblFindText.setObjectName(u"lblFindText")
        self.lblFindText.setMinimumSize(QSize(75, 0))

        self.horizontalLayout.addWidget(self.lblFindText)

        self.iptFindName = QLineEdit(TemplateReplacer)
        self.iptFindName.setObjectName(u"iptFindName")

        self.horizontalLayout.addWidget(self.iptFindName)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.lblReplaceText = QLabel(TemplateReplacer)
        self.lblReplaceText.setObjectName(u"lblReplaceText")
        self.lblReplaceText.setMinimumSize(QSize(75, 0))

        self.horizontalLayout_2.addWidget(self.lblReplaceText)

        self.iptReplaceName = QLineEdit(TemplateReplacer)
        self.iptReplaceName.setObjectName(u"iptReplaceName")

        self.horizontalLayout_2.addWidget(self.iptReplaceName)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lblObjectType = QLabel(TemplateReplacer)
        self.lblObjectType.setObjectName(u"lblObjectType")
        self.lblObjectType.setMinimumSize(QSize(75, 0))

        self.horizontalLayout_3.addWidget(self.lblObjectType)

        self.cbxObjectType = QComboBox(TemplateReplacer)
        self.cbxObjectType.setObjectName(u"cbxObjectType")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbxObjectType.sizePolicy().hasHeightForWidth())
        self.cbxObjectType.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.cbxObjectType)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.btnDoReplace = QPushButton(TemplateReplacer)
        self.btnDoReplace.setObjectName(u"btnDoReplace")

        self.verticalLayout.addWidget(self.btnDoReplace)


        self.retranslateUi(TemplateReplacer)

        QMetaObject.connectSlotsByName(TemplateReplacer)
    # setupUi

    def retranslateUi(self, TemplateReplacer):
        TemplateReplacer.setWindowTitle(QCoreApplication.translate("TemplateReplacer", u"\u6a21\u677f\u6279\u91cf\u66ff\u6362", None))
        self.lblFindText.setText(QCoreApplication.translate("TemplateReplacer", u"\u67e5\u627e\u5b57\u6bb5", None))
        self.lblReplaceText.setText(QCoreApplication.translate("TemplateReplacer", u"\u66ff\u6362\u6210", None))
        self.lblObjectType.setText(QCoreApplication.translate("TemplateReplacer", u"\u66ff\u6362\u5bf9\u8c61\u7c7b\u578b", None))
        self.btnDoReplace.setText(QCoreApplication.translate("TemplateReplacer", u"\u8fdb\u884c\u67e5\u627e\u66ff\u6362", None))
    # retranslateUi

