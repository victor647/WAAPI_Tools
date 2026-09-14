# 本文件由脚本生成，请勿手工修改。
# 数据来源：Wwise SDK 帮助文档 WwiseSDK-Windows.chm 的 "Wwise Objects Reference" 与
#          ak.wwise.core.object.get 的内置访问器列表。
# 生成脚本：.agents/skills/wwise-waapi/scripts/gen_object_properties.py
# 文档版本：2023.1.18.8899
#
# 用途：不向 Wwise 发请求就判断某个对象类型上是否存在某个属性/引用/列表（名称不区分大小写）。

SOURCE_VERSION = "2023.1.18.8899"

# 与对象类型无关的内置访问器（ak.wwise.core.object.get 的 return 可用名）
BUILTIN_ACCESSORS = frozenset((
    "activesource ancestors audiosource:language audiosource:maxdurationsource "
    "audiosource:maxradiusattenuation audiosource:playbackduration audiosource:trimvalues audiosourcelanguage "
    "audiosourcetrimvalues bnkfilepath category children childrencount classid contenthash context "
    "conversionhash convertedfilepath convertedwemfilepath descendants duration filepath id isdefault isdirty "
    "isexplicitmute isexplicitsolo isimplicitmute isimplicitsolo isincluded isplayable language loudness "
    "maxdurationsource maxdurationsourceobject maxradiusattenuation maxradiusattenuationobject mediaid "
    "mediasize music:playlistroot music:transitionroot musicplaylistroot musictransitionroot name nodetype "
    "notes objectsize originalfilepath originalrelativefilepath originalwavfilepath owner parent path "
    "playbackduration playlistroot pluginname points randomizer referencesto shortid "
    "sound:convertedwemfilepath sound:originalwavfilepath soundbank:bnkfilepath soundbankbnkfilepath "
    "stategroups stateproperties structuresize switchcontainerchild:context switchcontainerchildcontext this "
    "totalsize transitionroot trimvalues type validity workunit workunit:isdefault workunit:isdirty "
    "workunit:type workunitisdefault workunitisdirty workunittype "
).split())

# 对象类型（小写）-> 该类型可用的属性/引用/列表（小写）；Effect 与 SourcePlugin 已并入同族插件属性
TYPE_PROPERTIES = {
    "acoustictexture": frozenset((
        "absorptionhigh absorptionlow absorptionmidhigh absorptionmidlow absorptionoffset color overridecolor "
        "scattering "
    ).split()),
    "action": frozenset((
        "absoluteorrelative actiontype applytodynamicsequence applytostatetransition bypassflag "
        "bypassgameparameterinternaltransition delay effectslot fadeincurve fadeoutcurve fadetime "
        "gameparametervalue highpass inclusion lowpass masterresume pausedelayedresumeaction pitch probability "
        "resumestatetransition scope seekpercent seektime seektomarker seektype target targeteffect volume "
    ).split()),
    "actionexception": frozenset((
        "color overridecolor target "
    ).split()),
    "actormixer": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion effects enableattenuation enablediffraction enableloudnessnormalization "
        "enablemidinotetracking gameauxsendhpf gameauxsendlpf gameauxsendvolume hdractiverange hdrenableenvelope "
        "hdrenvelopesensitivity highpass holdemitterpositionorientation holdlistenerorientation "
        "ignoreparentmaxsoundinstance inclusion isgloballimit listenerrelativerouting loudnessnormalizationtarget "
        "loudnessnormalizationtype lowpass makeupgain maxreachedbehavior maxsoundperinstance metadata "
        "midibreakonnoteoff midichannelfilter midikeyfiltermax midikeyfiltermin midiplayonnotetype "
        "miditrackingrootnote miditransposition midivelocityfiltermax midivelocityfiltermin midivelocityoffset "
        "outputbus outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior overrideanalysis "
        "overridecolor overrideconversion overrideearlyreflections overrideeffect overridegameauxsends "
        "overridehdrenvelope overridemetadata overridemidieventsbehavior overridemidinotetracking overrideoutput "
        "overridepositioning overridepriority overrideuserauxsends overridevirtualvoice pitch priority "
        "prioritydistancefactor prioritydistanceoffset reflectionsauxsend reflectionsvolume rtpc speakerpanning "
        "speakerpanning3dspatializationmix usegameauxsends usemaxsoundperinstance userauxsend0 userauxsend1 "
        "userauxsend2 userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 "
        "userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 "
        "userauxsendvolume2 userauxsendvolume3 virtualvoicequeuebehavior volume "
    ).split()),
    "attenuation": frozenset((
        "color coneattenuation conehighpassfiltervalue coneinnerangle conelowpassfiltervalue coneouterangle "
        "coneuse heightspreadenable overridecolor radiusmax rtpc "
    ).split()),
    "audiodevice": frozenset((
        "bypasseffect color effects inclusion overridecolor rtpc "
    ).split()),
    "audiofilesource": frozenset((
        "channelconfigoverride color conversion crossfadeduration crossfadeshape fadeinduration fadeinshape "
        "fadeoutduration fadeoutshape hdrenvelope loopbegin loopend markerdetectionsensitivity markerinputmode "
        "markers overridecolor overrideconversion overridewavloop trimbegin trimend volumeoffset "
    ).split()),
    "auxbus": frozenset((
        "3dposition 3dspatialization attenuation buschannelconfig busvolume bypasseffect centerpercentage color "
        "effects enableattenuation enablediffraction gameauxsendhpf gameauxsendlpf gameauxsendvolume highpass "
        "holdemitterpositionorientation holdlistenerorientation listenerrelativerouting lowpass metadata "
        "outputbushighpass outputbuslowpass outputbusvolume overridecolor pitch reflectionsauxsend "
        "reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix usegameauxsends userauxsend0 "
        "userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 "
        "userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 "
        "userauxsendvolume2 userauxsendvolume3 volume "
    ).split()),
    "blendcontainer": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior blendbehavior bypasseffect "
        "centerpercentage color conversion effects enableattenuation enablediffraction "
        "enableloudnessnormalization enablemidinotetracking gameauxsendhpf gameauxsendlpf gameauxsendvolume "
        "hdractiverange hdrenableenvelope hdrenvelopesensitivity highpass holdemitterpositionorientation "
        "holdlistenerorientation ignoreparentmaxsoundinstance inclusion initialdelay isgloballimit "
        "listenerrelativerouting loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain "
        "maxreachedbehavior maxsoundperinstance metadata midibreakonnoteoff midichannelfilter midikeyfiltermax "
        "midikeyfiltermin midiplayonnotetype miditrackingrootnote miditransposition midivelocityfiltermax "
        "midivelocityfiltermin midivelocityoffset outputbus outputbushighpass outputbuslowpass outputbusvolume "
        "overlimitbehavior overrideanalysis overridecolor overrideconversion overrideearlyreflections "
        "overrideeffect overridegameauxsends overridehdrenvelope overridemetadata overridemidieventsbehavior "
        "overridemidinotetracking overrideoutput overridepositioning overridepriority overrideuserauxsends "
        "overridevirtualvoice pitch priority prioritydistancefactor prioritydistanceoffset reflectionsauxsend "
        "reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix usegameauxsends "
        "usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 "
        "userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 "
        "userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 userauxsendvolume3 "
        "virtualvoicequeuebehavior volume weight "
    ).split()),
    "blendtrack": frozenset((
        "enablecrossfading highpass layercrossfadecontrolinput lowpass makeupgain pitch rtpc volume "
    ).split()),
    "bus": frozenset((
        "3dposition 3dspatialization attenuation audiodevice buschannelconfig busvolume bypasseffect "
        "centerpercentage color effects enableattenuation enablediffraction gameauxsendhpf gameauxsendlpf "
        "gameauxsendvolume hdrenable hdroutputgameparametermax hdroutputgameparametermin "
        "hdrpeakoutputgameparameter hdrratio hdrreleasetime hdrreleasetimemode hdrthreshold highpass "
        "holdemitterpositionorientation holdlistenerorientation ignoreparentmaxsoundinstance "
        "listenerrelativerouting lowpass makeupgain maxduckvolume maxreachedbehavior maxsoundperinstance metadata "
        "outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior overridecolor pitch recoverytime "
        "reflectionsauxsend reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix "
        "usedforbackgroundmusic usegameauxsends usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 "
        "userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 "
        "userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 "
        "userauxsendvolume3 volume "
    ).split()),
    "controlsurfacebinding": frozenset((
        "color hardwarecontrollerkey objectindexinview overridecolor targetclassid targetname targetobject "
        "targettype "
    ).split()),
    "controlsurfacebindinggroup": frozenset((
        "color grouptype hardwarecontrollerkey objectindexinview overridecolor targetclassid targetname "
        "targettype "
    ).split()),
    "controlsurfacesession": frozenset((
        "color overridecolor "
    ).split()),
    "conversion": frozenset((
        "allowchannelupmix channels color lrmix maxsamplerate minsamplerate overridecolor removedcoffset "
        "samplerate srconversionquality usedither usefilenamemarker "
    ).split()),
    "curve": frozenset((
        "flags "
    ).split()),
    "customstate": frozenset(),
    "dialogueevent": frozenset((
        "arguments color entries mode overridecolor probability "
    ).split()),
    "effect": frozenset((
        "algotypeselect ambisonicschannelordering applydownstreamvolume attacktime authoringfilename "
        "basetexturefrequency center centerlevel centerperc channelconfigoverride channellink color "
        "compressorband1attack compressorband1enabled compressorband1knee compressorband1makeupgain "
        "compressorband1ratio compressorband1release compressorband1threshold compressorband2attack "
        "compressorband2enabled compressorband2knee compressorband2makeupgain compressorband2ratio "
        "compressorband2release compressorband2threshold compressorband3attack compressorband3enabled "
        "compressorband3knee compressorband3makeupgain compressorband3ratio compressorband3release "
        "compressorband3threshold compressorband4attack compressorband4enabled compressorband4knee "
        "compressorband4makeupgain compressorband4ratio compressorband4release compressorband4threshold "
        "compressorcrossoverfrequency1 compressorcrossoverfrequency2 compressorcrossoverfrequency3 "
        "compressorlinkmode compressorlinkstereopairs compressorlinkstrength compressornumbands curveusagemask "
        "dcfiltercutfreq decaytime decorralgorithmselect decorrfiltermaxreflectionorder "
        "decorrhardwareacceleration decorrstrength decorrstrengthsource decorrwindowwidth delaylengthsmode "
        "delaytime delaytime1 delaytime10 delaytime11 delaytime12 delaytime13 delaytime14 delaytime15 delaytime16 "
        "delaytime2 delaytime3 delaytime4 delaytime5 delaytime6 delaytime7 delaytime8 delaytime9 density "
        "densitydelaymax densitydelaymin densitydelayrdmperc diffractionwarping diffusion diffusiondelaymax "
        "diffusiondelayrdmperc diffusiondelayscaleperc distancethreshold distancewarping distortiondrive "
        "distortiontone distortiontype downmixtostereo dry drylevel enablecrossfeed enableearlyreflections "
        "enablefeedback enablelfo enabletonecontrols erfrontbackdelay erlevel erpattern feedback feedbackenabled "
        "feedbacklevel feedforwardlevel filter1curve filter1freq filter1gain filter1insertpos filter1q "
        "filter2curve filter2freq filter2gain filter2insertpos filter2q filter3curve filter3freq filter3gain "
        "filter3insertpos filter3q filterfrequency filtergain filterqfactor filtertype filtertypeband1 "
        "filtertypeband2 filtertypeband3 format frequencyband1 frequencyband2 frequencyband3 front frontlevel "
        "frontrearbalance frontreardelay fullbandgain fullprecisionmedia fusingtime gainband1 gainband2 gainband3 "
        "gamefilename hardwareacceleration hfdamping hfratio hold inclusion infinitehold input inputcenterlevel "
        "inputlfelevel inputstereowidth inputthreshold irchannelselect irconvolutionsmooth irconvolutionsmoothmax "
        "irconvolutionstart irconvolutionstop irconvolutionthreshold irgraphiceqautomate irlevel irlevelautomate "
        "irlpfautomate irlpfslope irlrmix irstretch leftcrossfeed leftdelaytime leftfeedback leftinputtype lfe "
        "lfegain lfelevel limiterattack limiterlinkchannels limitermode limiteroutputgain limiterrelease "
        "limiterthreshold lookahead mainmixconfiguration mastervolumechannel1 mastervolumechannel10 "
        "mastervolumechannel11 mastervolumechannel12 mastervolumechannel2 mastervolumechannel3 "
        "mastervolumechannel4 mastervolumechannel5 mastervolumechannel6 mastervolumechannel7 mastervolumechannel8 "
        "mastervolumechannel9 max maxdistance maxreflections metermode meterscope min moddepth modfrequency "
        "modphasemode modphaseoffset modphasespread modpwm modsmoothing moduleenablecompressor "
        "moduleenablelimiter moduleenablemastervolume moduleenableparameq modwaveform numberofdelays onoffband1 "
        "onoffband2 onoffband3 outputchannelconfig outputgain outputlevel overridecolor paramband1enabled "
        "paramband1filtermode paramband1frequency paramband1gain paramband1resonance paramband2enabled "
        "paramband2filtermode paramband2frequency paramband2gain paramband2resonance paramband3enabled "
        "paramband3filtermode paramband3frequency paramband3gain paramband3resonance paramband4enabled "
        "paramband4filtermode paramband4frequency paramband4gain paramband4resonance paramband5enabled "
        "paramband5filtermode paramband5frequency paramband5gain paramband5resonance paramband6enabled "
        "paramband6filtermode paramband6frequency paramband6gain paramband6resonance parameqnumbands "
        "paramfiltercutoff paramfiltertype passthroughmixpolicy pitch pitchshift pitchshiftrandom pitchthreshold "
        "posteqband1enable posteqband1filtertype posteqband1frequency posteqband1gain posteqband1qfactor "
        "posteqband2enable posteqband2filtertype posteqband2frequency posteqband2gain posteqband2qfactor "
        "posteqband3enable posteqband3filtertype posteqband3frequency posteqband3gain posteqband3qfactor predelay "
        "preeqband1enable preeqband1filtertype preeqband1frequency preeqband1gain preeqband1qfactor "
        "preeqband2enable preeqband2filtertype preeqband2frequency preeqband2gain preeqband2qfactor "
        "preeqband3enable preeqband3filtertype preeqband3frequency preeqband3gain preeqband3qfactor processcenter "
        "processlfe qfactorband1 qfactorband2 qfactorband3 quality qualityenable ratio rear rearlevel "
        "rectification releasetime reverblevel reverbtime reverbunitinputdelay reverbunitinputdelayrmdperc "
        "rightcrossfeed rightdelaytime rightfeedback rightinputtype roomshape roomshapemax roomshapemin roomsize "
        "rtpc soundengineblocksize soundenginesampleratedefault soundenginesamplerateios soundenginesampleratemac "
        "speedofsound stereodecorrelation stereoprocessing stereowidth surround syncdry systemaudioobjectlimit "
        "systemaudioobjectspolicy threshold thresholdmode timestretch timestretchrandom voice1enable "
        "voice1filterfrequency voice1filtergain voice1filterqfactor voice1filtertype voice1gain voice1pitch "
        "voice2enable voice2filterfrequency voice2filtergain voice2filterqfactor voice2filtertype voice2gain "
        "voice2pitch wet wetdrymix wetlevel windowsize "
    ).split()),
    "effectslot": frozenset((
        "bypass effect render rtpc "
    ).split()),
    "event": frozenset((
        "color inclusion overridecolor "
    ).split()),
    "externalsource": frozenset(),
    "externalsourcefile": frozenset((
        "analysistype conversion loudnessnormalizationtarget loudnessnormalizationtype overrideconversion "
    ).split()),
    "folder": frozenset((
        "color inclusion overridecolor "
    ).split()),
    "gameparameter": frozenset((
        "bindtobuiltinparam color filtertimedown filtertimeup initialvalue max min overridecolor rtpcramping "
        "simulationvalue slewratedown slewrateup "
    ).split()),
    "language": frozenset((
        "volumeoffset "
    ).split()),
    "marker": frozenset((
        "color label overridecolor time "
    ).split()),
    "metadata": frozenset((
        "color inclusion overridecolor rtpc "
    ).split()),
    "midifilesource": frozenset(),
    "midiparameter": frozenset((
        "simulationvalue "
    ).split()),
    "mixingsession": frozenset((
        "color overridecolor "
    ).split()),
    "modifier": frozenset((
        "enabled max min "
    ).split()),
    "modulatorenvelope": frozenset((
        "color envelopeattackcurve envelopeattacktime envelopeautorelease envelopedecaytime envelopereleasetime "
        "envelopestopplayback envelopesustainlevel envelopesustaintime envelopetriggeron modulatorscope "
        "overridecolor rtpc "
    ).split()),
    "modulatorlfo": frozenset((
        "color lfoattack lfodepth lfofrequency lfoinitialphase lfopwm lfosmoothing lfowaveform modulatorscope "
        "overridecolor rtpc "
    ).split()),
    "modulatortime": frozenset((
        "color envelopestopplayback envelopetriggeron modulatorscope overridecolor rtpc timemodduration "
        "timemodinitialdelay timemodloops timemodplaybackrate "
    ).split()),
    "multiswitchentry": frozenset((
        "audionode entrypath probability weight "
    ).split()),
    "musicclip": frozenset((
        "begintrimoffset color endtrimoffset fadeinduration fadeinmode fadeinshape fadeoutduration fadeoutmode "
        "fadeoutshape highpass lowpass overridecolor playat volume "
    ).split()),
    "musicclipmidi": frozenset((
        "begintrimoffset color endtrimoffset overridecolor playat "
    ).split()),
    "musiccue": frozenset((
        "color cuetype overridecolor timems "
    ).split()),
    "musiceventcue": frozenset((
        "playat posteventtarget "
    ).split()),
    "musicfade": frozenset((
        "fadecurve fadeoffset fadetime fadetype "
    ).split()),
    "musicplaylistcontainer": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion effects enableattenuation enablediffraction enableloudnessnormalization gameauxsendhpf "
        "gameauxsendlpf gameauxsendvolume gridfrequencypreset gridoffsetcustom gridoffsetpreset hdractiverange "
        "hdrenableenvelope hdrenvelopesensitivity highpass holdemitterpositionorientation holdlistenerorientation "
        "ignoreparentmaxsoundinstance inclusion isgloballimit listenerrelativerouting loudnessnormalizationtarget "
        "loudnessnormalizationtype lowpass makeupgain maxreachedbehavior maxsoundperinstance metadata miditarget "
        "miditemposource outputbus outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior "
        "overrideanalysis overrideclocksettings overridecolor overrideconversion overrideearlyreflections "
        "overrideeffect overridegameauxsends overridehdrenvelope overridemetadata overridemiditarget "
        "overridemiditempo overrideoutput overridepositioning overridepriority overrideuserauxsends "
        "overridevirtualvoice playbackspeed playlistroot priority prioritydistancefactor prioritydistanceoffset "
        "reflectionsauxsend reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix stingers "
        "tempo timesignaturelower timesignatureupper transitionroot usegameauxsends usemaxsoundperinstance "
        "userauxsend0 userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 "
        "userauxsendhpf3 userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 "
        "userauxsendvolume1 userauxsendvolume2 userauxsendvolume3 virtualvoicequeuebehavior volume "
    ).split()),
    "musicplaylistitem": frozenset((
        "color loopcount normalorshuffle overridecolor playlistitemtype playmode randomavoidrepeatingcount "
        "segment weight "
    ).split()),
    "musicsegment": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion cues effects enableattenuation enablediffraction enableloudnessnormalization endposition "
        "gameauxsendhpf gameauxsendlpf gameauxsendvolume gridfrequencypreset gridoffsetcustom gridoffsetpreset "
        "hdractiverange hdrenableenvelope hdrenvelopesensitivity highpass holdemitterpositionorientation "
        "holdlistenerorientation ignoreparentmaxsoundinstance inclusion isgloballimit listenerrelativerouting "
        "loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain maxreachedbehavior "
        "maxsoundperinstance metadata miditarget miditemposource outputbus outputbushighpass outputbuslowpass "
        "outputbusvolume overlimitbehavior overrideanalysis overrideclocksettings overridecolor "
        "overrideconversion overrideearlyreflections overrideeffect overridegameauxsends overridehdrenvelope "
        "overridemetadata overridemiditarget overridemiditempo overrideoutput overridepositioning "
        "overridepriority overrideuserauxsends overridevirtualvoice playbackspeed priority prioritydistancefactor "
        "prioritydistanceoffset reflectionsauxsend reflectionsvolume rtpc speakerpanning "
        "speakerpanning3dspatializationmix stingers tempo timesignaturelower timesignatureupper usegameauxsends "
        "usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 "
        "userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 "
        "userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 userauxsendvolume3 "
        "virtualvoicequeuebehavior volume "
    ).split()),
    "musicstinger": frozenset((
        "color customcuematchname dontplayagaintime numsegmentadvance overridecolor playsegmentat segment trigger "
    ).split()),
    "musicswitchcontainer": frozenset((
        "3dposition 3dspatialization arguments attenuation belowthresholdbehavior bypasseffect centerpercentage "
        "color continueplay conversion effects enableattenuation enablediffraction enableloudnessnormalization "
        "entries gameauxsendhpf gameauxsendlpf gameauxsendvolume gridfrequencypreset gridoffsetcustom "
        "gridoffsetpreset hdractiverange hdrenableenvelope hdrenvelopesensitivity highpass "
        "holdemitterpositionorientation holdlistenerorientation ignoreparentmaxsoundinstance inclusion "
        "isgloballimit listenerrelativerouting loudnessnormalizationtarget loudnessnormalizationtype lowpass "
        "makeupgain maxreachedbehavior maxsoundperinstance metadata miditarget miditemposource mode outputbus "
        "outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior overrideanalysis "
        "overrideclocksettings overridecolor overrideconversion overrideearlyreflections overrideeffect "
        "overridegameauxsends overridehdrenvelope overridemetadata overridemiditarget overridemiditempo "
        "overrideoutput overridepositioning overridepriority overrideuserauxsends overridevirtualvoice "
        "playbackspeed priority prioritydistancefactor prioritydistanceoffset reflectionsauxsend "
        "reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix stingers tempo "
        "timesignaturelower timesignatureupper transitionroot usegameauxsends usemaxsoundperinstance userauxsend0 "
        "userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 "
        "userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 "
        "userauxsendvolume2 userauxsendvolume3 virtualvoicequeuebehavior volume "
    ).split()),
    "musictrack": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion defaultswitchorstate effects enableattenuation enablediffraction enableloudnessnormalization "
        "gameauxsendhpf gameauxsendlpf gameauxsendvolume hdractiverange hdrenableenvelope hdrenvelopesensitivity "
        "highpass holdemitterpositionorientation holdlistenerorientation ignoreparentmaxsoundinstance inclusion "
        "isgloballimit isnoncachable isstreamingenabled iszerolatency listenerrelativerouting lookaheadtime "
        "loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain maxreachedbehavior "
        "maxsoundperinstance metadata miditarget miditemposource musictracktype outputbus outputbushighpass "
        "outputbuslowpass outputbusvolume overlimitbehavior overrideanalysis overridecolor overrideconversion "
        "overrideearlyreflections overrideeffect overridegameauxsends overridehdrenvelope overridemetadata "
        "overridemiditarget overridemiditempo overrideoutput overridepositioning overridepriority "
        "overrideuserauxsends overridevirtualvoice prefetchlength priority prioritydistancefactor "
        "prioritydistanceoffset reflectionsauxsend reflectionsvolume rtpc sequences speakerpanning "
        "speakerpanning3dspatializationmix switchgrouporstategroup transitionroot usegameauxsends "
        "usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 userauxsend3 userauxsendhpf0 "
        "userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 "
        "userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 userauxsendvolume3 "
        "virtualvoicequeuebehavior volume "
    ).split()),
    "musictracksequence": frozenset((
        "clips color overridecolor tracksequenceswitch "
    ).split()),
    "musictransition": frozenset((
        "color destinationcontextobject destinationcontexttype destinationjumppositionpreset "
        "destinationplaylistjumpto enabledestinationfadein enablesourcefadeout enabletransitionfadein "
        "enabletransitionfadeout exitsourceat exitsourcecustomcuematchname isfolder jumptocustomcuematchmode "
        "jumptocustomcuematchname overridecolor playdestinationpreentry playsourcepostexit playtransitionpostexit "
        "playtransitionpreentry sourcecontextobject sourcecontexttype usetransitionobject "
    ).split()),
    "objectsettingassoc": frozenset((
        "continueplay fadeintime fadeouttime firstoccurenceonly onswitchchange "
    ).split()),
    "panner": frozenset((
        "panx pany panz rtpc "
    ).split()),
    "path2d": frozenset((
        "appendoffset duration flags lineartime randomx randomy randomz "
    ).split()),
    "platform": frozenset(),
    "plugindatasource": frozenset((
        "datafilename "
    ).split()),
    "position": frozenset((
        "newpathforeachsound panx pany panz playmechanismloop playmechanismrandomorsequence "
        "playmechanismsteporcontinuous playmechanismtransitiontime playmechanismtransitionuse rtpc "
    ).split()),
    "project": frozenset((
        "alwayssavemediaidsfile autodetectfftwindowsize autodetectthresholdhigh autodetectthresholdlow "
        "autodetectthresholdmedium autosoundbankallevents autosoundbankenabled color commportdiscoverybroadcast "
        "commportdiscoveryresponse commserialportbase copyloosestreamedmedia defaultlanguage "
        "eventactionnameposition eventnamecasetype eventnamemodifycase externalsourcesinputpath "
        "externalsourcesoutputpath filterbehavior generatemainsoundbank generatemultiplebanks "
        "generatesoundbankjson generatesoundbankxml globalvoiceinstanceslimit licensekey lineending "
        "maxdangerousvirtualvoices maxmessagespermessageid mediaautobanksubfolders mediaidsinsinglefile "
        "overridecolor removeunusedgeneratedfiles soundbankallowexceedingsb soundbankdefinitionfileformat "
        "soundbankgeneratedefinitionfile soundbankgenerateestimatedduration soundbankgenerateheaderfile "
        "soundbankgeneratemaxattenuationinfo soundbankgenerateprintguid soundbankgenerateprintpath "
        "soundbankgeneratereadablefile soundbankheaderfilepath soundbankincludesoundbanknamesstrings "
        "soundbankpaths soundbankpostgeneratecustomcmddescription soundbankpostgeneratecustomcmdlines "
        "soundbankpregeneratecustomcmddescription soundbankpregeneratecustomcmdlines soundbankupdateaudiofiles "
        "sourcecontrolgeneratedfiles useactionnameforevent usedefaultlanguage usemaxdangerousvirtualvoices "
        "usemaxmessagespermessageid volumethreshold wwiseconsoleloadusersettings wwiseversionwhencreated "
    ).split()),
    "query": frozenset((
        "color logicaloperator objecttype overridecolor platform startobject waql "
    ).split()),
    "randomsequencecontainer": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion effects enableattenuation enablediffraction enableloudnessnormalization "
        "enablemidinotetracking gameauxsendhpf gameauxsendlpf gameauxsendvolume globalorperobject hdractiverange "
        "hdrenableenvelope hdrenvelopesensitivity highpass holdemitterpositionorientation holdlistenerorientation "
        "ignoreparentmaxsoundinstance inclusion initialdelay isgloballimit listenerrelativerouting "
        "loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain maxreachedbehavior "
        "maxsoundperinstance metadata midibreakonnoteoff midichannelfilter midikeyfiltermax midikeyfiltermin "
        "midiplayonnotetype miditrackingrootnote miditransposition midivelocityfiltermax midivelocityfiltermin "
        "midivelocityoffset normalorshuffle outputbus outputbushighpass outputbuslowpass outputbusvolume "
        "overlimitbehavior overrideanalysis overridecolor overrideconversion overrideearlyreflections "
        "overrideeffect overridegameauxsends overridehdrenvelope overridemetadata overridemidieventsbehavior "
        "overridemidinotetracking overrideoutput overridepositioning overridepriority overrideuserauxsends "
        "overridevirtualvoice pitch playlist playmechanisminfiniteornumberofloops playmechanismloop "
        "playmechanismloopcount playmechanismresetplaylisteachplay playmechanismspecialtransitions "
        "playmechanismspecialtransitionstype playmechanismspecialtransitionsvalue playmechanismsteporcontinuous "
        "priority prioritydistancefactor prioritydistanceoffset randomavoidrepeating randomavoidrepeatingcount "
        "randomorsequence reflectionsauxsend reflectionsvolume restartbeginningorbackward rtpc speakerpanning "
        "speakerpanning3dspatializationmix usegameauxsends usemaxsoundperinstance userauxsend0 userauxsend1 "
        "userauxsend2 userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 "
        "userauxsendlpf0 userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 "
        "userauxsendvolume2 userauxsendvolume3 virtualvoicequeuebehavior volume weight "
    ).split()),
    "rtpc": frozenset((
        "color controlinput curve overridecolor propertyname "
    ).split()),
    "searchcriteria": frozenset((
        "attenuation conditionaloperator conversion curvetype curveusage defaultswitchstate effect effectclassid "
        "eventsreferencedinoperator gameparameter hasemptyassignation inclusion ischecked islinked "
        "issourceofoverride isspecialsearch isused leftvalue logicaloperator metadata metadataclassid mode "
        "musicsegment numericoperator objectreferenced outputbus propertyname rightvalue rndseqcontainertype "
        "rtpcoperator samplerateconversiontype soundtype sourceaudioformat sourcechannelslfeoption "
        "sourcechannelsotherscount sourcechannelsothersoption sourcelanguage sourcetype srconversionquality state "
        "stategroup statepropertyusage switchgroup switchingoperator trigger uintvalue userstring usingoperator "
    ).split()),
    "sound": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion effects enableattenuation enablediffraction enableloudnessnormalization "
        "enablemidinotetracking gameauxsendhpf gameauxsendlpf gameauxsendvolume hdractiverange hdrenableenvelope "
        "hdrenvelopesensitivity highpass holdemitterpositionorientation holdlistenerorientation "
        "ignoreparentmaxsoundinstance inclusion initialdelay isgloballimit isloopingenabled isloopinginfinite "
        "isnoncachable isstreamingenabled isvoice iszerolatency listenerrelativerouting loopcount "
        "loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain maxreachedbehavior "
        "maxsoundperinstance metadata midibreakonnoteoff midichannelfilter midikeyfiltermax midikeyfiltermin "
        "midiplayonnotetype miditrackingrootnote miditransposition midivelocityfiltermax midivelocityfiltermin "
        "midivelocityoffset outputbus outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior "
        "overrideanalysis overridecolor overrideconversion overrideearlyreflections overrideeffect "
        "overridegameauxsends overridehdrenvelope overridemetadata overridemidieventsbehavior "
        "overridemidinotetracking overrideoutput overridepositioning overridepriority overrideuserauxsends "
        "overridevirtualvoice pitch prefetchlength priority prioritydistancefactor prioritydistanceoffset "
        "reflectionsauxsend reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix "
        "usegameauxsends usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 userauxsend3 "
        "userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 userauxsendlpf1 "
        "userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 "
        "userauxsendvolume3 virtualvoicequeuebehavior volume weight "
    ).split()),
    "soundbank": frozenset((
        "color fill maximum overridecolor "
    ).split()),
    "soundcastersession": frozenset((
        "color overridecolor "
    ).split()),
    "sourceplugin": frozenset((
        "amplitude amplitudemod1depth amplitudemod1quantization amplitudemod2depth amplitudemod2quantization "
        "amplitudemod3depth amplitudemod3quantization amplitudemod4depth amplitudemod4quantization attack "
        "attackmod1depth attackmod1quantization attackmod2depth attackmod2quantization attackmod3depth "
        "attackmod3quantization attackmod4depth attackmod4quantization attacktime attenuationrolloff "
        "averagevelocity averagevelocityautomate averagevelocityrandom azimuth azimuthmod1depth "
        "azimuthmod1quantization azimuthmod2depth azimuthmod2quantization azimuthmod3depth "
        "azimuthmod3quantization azimuthmod4depth azimuthmod4quantization basefrequency channel1 channel2 "
        "channel3 channel4 channelconfig channelmask color decaytime direction directionautomate directionrandom "
        "distanceattenuation drivera driverb driverc driverd drivere driverf driverg driverh duration "
        "durationlink durationmod1depth durationmod1quantization durationmod2depth durationmod2quantization "
        "durationmod3depth durationmod3quantization durationmod4depth durationmod4quantization durationmultiplier "
        "durationmultipliermod1depth durationmultipliermod1quantization durationmultipliermod2depth "
        "durationmultipliermod2quantization durationmultipliermod3depth durationmultipliermod3quantization "
        "durationmultipliermod4depth durationmultipliermod4quantization durationrandom durmode elevation "
        "elevationmod1depth elevationmod1quantization elevationmod2depth elevationmod2quantization "
        "elevationmod3depth elevationmod3quantization elevationmod4depth elevationmod4quantization envelopetype "
        "excitationmask excitationselectionmode fileexcitation filemodel filterfreq filterfreqmod1depth "
        "filterfreqmod1quantization filterfreqmod2depth filterfreqmod2quantization filterfreqmod3depth "
        "filterfreqmod3quantization filterfreqmod4depth filterfreqmod4quantization filterq filterqmod1depth "
        "filterqmod1quantization filterqmod2depth filterqmod2quantization filterqmod3depth "
        "filterqmod3quantization filterqmod4depth filterqmod4quantization filtertype fixdur fmamount fmdepth "
        "fmdepthrandom frequencymode frequencyscale frequencyscaleautomate frequencyscalerandom gainoffset "
        "gainoffsetautomate gainoffsetrandom grainrate grainratemod1depth grainratemod1quantization "
        "grainratemod2depth grainratemod2quantization grainratemod3depth grainratemod3quantization "
        "grainratemod4depth grainratemod4quantization graintime graintimemod1depth graintimemod1quantization "
        "graintimemod2depth graintimemod2quantization graintimemod3depth graintimemod3quantization "
        "graintimemod4depth graintimemod4quantization gustiness gustinessautomate gustinessrandom high1 high2 "
        "impactposition impactpositionrandom lefttrigger length lengthmax lengthmin low1 low2 markerselect "
        "markerselectmod1depth markerselectmod1quantization markerselectmod2depth markerselectmod2quantization "
        "markerselectmod3depth markerselectmod3quantization markerselectmod4depth markerselectmod4quantization "
        "mass massrandom maxdistance maxnumgrains midimaptranspose mindistance minduration modamount1 modamount2 "
        "modamount3 modamount4 modelmask modelselectionmode modperiod1 modperiod2 modperiod3 modperiod4 modrate1 "
        "modrate2 modrate3 modrate4 modselect1 modselect2 modselect3 modselect4 modwaveform1 modwaveform2 "
        "modwaveform3 modwaveform4 noisecolor noiselevel noiseshape numfiles offset offsetmod1depth "
        "offsetmod1quantization offsetmod2depth offsetmod2quantization offsetmod3depth offsetmod3quantization "
        "offsetmod4depth offsetmod4quantization operationmode osc1invert osc1level osc1pwm osc1transpose "
        "osc1waveform osc2invert osc2level osc2pwm osc2transpose osc2waveform outputchannelconfig outputlevel "
        "overridecolor oversampling playbackrate positioningselect qfactorscale qfactorscaleautomate "
        "qfactorscalerandom quantizetomarkers release releasemod1depth releasemod1quantization releasemod2depth "
        "releasemod2quantization releasemod3depth releasemod3quantization releasemod4depth "
        "releasemod4quantization releasetime righttrigger rtpc selectfreqtimegrain speed speedautomate "
        "speedmod1depth speedmod1quantization speedmod2depth speedmod2quantization speedmod3depth "
        "speedmod3quantization speedmod4depth speedmod4quantization speedpointspeedrandom speedpointtimerandom "
        "speedrandom spread spreadmod1depth spreadmod1quantization spreadmod2depth spreadmod2quantization "
        "spreadmod3depth spreadmod3quantization spreadmod4depth spreadmod4quantization startfreq startfreqrandmax "
        "startfreqrandmin stopfreq stopfreqrandmax stopfreqrandmin sustainlevel sustaintime sweepfreq "
        "sweepfreqtype transpose transposemod1depth transposemod1quantization transposemod2depth "
        "transposemod2quantization transposemod3depth transposemod3quantization transposemod4depth "
        "transposemod4quantization transposeroot variability variabilityautomate variabilityrandom velocity "
        "velocitydynamicrange velocityrandom wavegain wavetype windowmode "
    ).split()),
    "state": frozenset((
        "color overridecolor "
    ).split()),
    "stategroup": frozenset((
        "color defaulttransitiontime overridecolor "
    ).split()),
    "switch": frozenset((
        "color overridecolor "
    ).split()),
    "switchcontainer": frozenset((
        "3dposition 3dspatialization attenuation belowthresholdbehavior bypasseffect centerpercentage color "
        "conversion defaultswitchorstate effects enableattenuation enablediffraction enableloudnessnormalization "
        "enablemidinotetracking gameauxsendhpf gameauxsendlpf gameauxsendvolume hdractiverange hdrenableenvelope "
        "hdrenvelopesensitivity highpass holdemitterpositionorientation holdlistenerorientation "
        "ignoreparentmaxsoundinstance inclusion initialdelay isgloballimit listenerrelativerouting "
        "loudnessnormalizationtarget loudnessnormalizationtype lowpass makeupgain maxreachedbehavior "
        "maxsoundperinstance metadata midibreakonnoteoff midichannelfilter midikeyfiltermax midikeyfiltermin "
        "midiplayonnotetype miditrackingrootnote miditransposition midivelocityfiltermax midivelocityfiltermin "
        "midivelocityoffset outputbus outputbushighpass outputbuslowpass outputbusvolume overlimitbehavior "
        "overrideanalysis overridecolor overrideconversion overrideearlyreflections overrideeffect "
        "overridegameauxsends overridehdrenvelope overridemetadata overridemidieventsbehavior "
        "overridemidinotetracking overrideoutput overridepositioning overridepriority overrideuserauxsends "
        "overridevirtualvoice pitch priority prioritydistancefactor prioritydistanceoffset reflectionsauxsend "
        "reflectionsvolume rtpc speakerpanning speakerpanning3dspatializationmix switchbehavior "
        "switchgrouporstategroup usegameauxsends usemaxsoundperinstance userauxsend0 userauxsend1 userauxsend2 "
        "userauxsend3 userauxsendhpf0 userauxsendhpf1 userauxsendhpf2 userauxsendhpf3 userauxsendlpf0 "
        "userauxsendlpf1 userauxsendlpf2 userauxsendlpf3 userauxsendvolume0 userauxsendvolume1 userauxsendvolume2 "
        "userauxsendvolume3 virtualvoicequeuebehavior volume weight "
    ).split()),
    "switchgroup": frozenset((
        "color overridecolor usegameparameter "
    ).split()),
    "trigger": frozenset((
        "color overridecolor "
    ).split()),
    "userprojectsettings": frozenset((
        "autosoundbankallevents autosoundbankenabled conversion convertexternalsources copyloosestreamedmedia "
        "defaultsoundvolume eventactionnameposition eventcreationsettingsoverride eventnamecasetype "
        "eventnamemodifycase externalsourcesinputpath externalsourcesoutputpath externalsourcesoverrideinputpath "
        "externalsourcesoverrideoutputpath generatemainsoundbank generatemultiplebanks generatesoundbankjson "
        "generatesoundbankxml mediaautobanksubfolders overrideconversion postgeneratestepuseroverride "
        "pregeneratestepuseroverride removeunusedgeneratedfiles settingsuseroverride soundbankallowexceedingsb "
        "soundbankdefinitionfileformat soundbankgeneratedefinitionfile soundbankgenerateestimatedduration "
        "soundbankgenerateheaderfile soundbankgeneratemaxattenuationinfo soundbankgenerateprintguid "
        "soundbankgenerateprintpath soundbankgeneratereadablefile soundbankheaderfilepath "
        "soundbankincludesoundbanknamesstrings soundbankpaths soundbankpathuseroverride "
        "soundbankpostgeneratecustomcmddescription soundbankpostgeneratecustomcmdlines "
        "soundbankpregeneratecustomcmddescription soundbankpregeneratecustomcmdlines soundbankupdateaudiofiles "
        "sourcecontrolgeneratedfiles useactionnameforevent "
    ).split()),
    "workunit": frozenset((
        "color inclusion overridecolor "
    ).split()),
}
