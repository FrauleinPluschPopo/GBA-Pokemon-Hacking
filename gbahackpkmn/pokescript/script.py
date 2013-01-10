
from gbahackpkmn.pokescript.routine import Routine
from gbahackpkmn.strings import PokeString
from gbahackpkmn.movements import Movement as PokeMovement

from gbahackpkmn.pokescript.ast import *
from gbahackpkmn.pokescript.decompiler import Decompiler, DecompileTypes

def loadGroup(rom, routinepointer):
    '''
    Decompiles a Pokescript at the given routinepointer, also loads
    related Resources (routines, strings, and movements) from the ROM and 
    stores them into the resource group.
    
    Returns a new scriptgroup with all elements loaded.
    '''        
    decompiler = Decompiler(rom)
    decompilequeue = []    #Group of elements to decompile, stored in the queue
    decompiled = {}        #Group of loaded pointers and their resources
    sgroup = ScriptGroup() #ScriptGroup where all resources are added to
    
    decompilequeue.append((routinepointer, DecompileTypes.POKESCRIPT))
        
    while len(decompilequeue) > 0:
        pointer, dtype = decompilequeue.pop()
        
        if pointer in decompiled:    #skip if already decompiled.
            continue
            
        resource = decompiler.decompile(pointer, dtype)
        decompiled[pointer] = resource
        sgroup.register(resource, pointer)
        
        #some resources, such as the Routine, link to others.
        # queue those others.
        if isinstance(resource, Routine):
            for refpointer, reftype in resource.linkedPointers():
                decompilequeue.append((refpointer, reftype))

    #At this point, all resources are loaded.
    # Replace, where possible, all pointerrefs to their corresponding
    # varname refs.
    sgroup.pointers2varnames()
    return sgroup



class ScriptGroup():
    '''
    The scriptgroup keeps track of a (group of) scripts, and related
    resources. It can keep track of objects in a ROM, or unstored objects.
    
    The save() operation stores all objects in the ROM, and makes sure
    that pointers of all elements registered to the ScriptGroup are updated.
    '''
    
    def __init__(self):      
        #List of already ROM-stored loaded routines, strings, etc.
        #  Stored format: index: varname, value: (resource, pointer)
        #                 if not stored in rom: pointer = None
        self._resources = {}
        
        #A list of counters per resource type, used to generate varnames.
        self._namecounters = {}
        
    
    def register(self, resource, pointer=None, varname=None):
        '''
        Registers a Resource object to the ScriptGroup.
        If varname is None, a varname is generated, otherwise the given one is
        used.
        Returns a new unique (generated) varname for the registered resource.
        '''
        if varname == None and len(self._resources)==0:
            varname = "$start"
        elif varname == None:
            if resource.name not in self._namecounters:
                self._namecounters[resource.name] = 0
            varname = "$%s_%d"%(resource.name, self._namecounters[resource.name])
            self._namecounters[resource.name] += 1
        else:
            varname = str(varname)
        
        if varname in self._resources:
            raise Exception("Varname %s is already in use."%varname)
        
        self._resources[varname] = (resource, pointer)
        
        return varname
    
    
    def setPointer(self, varname, pointer):
        '''Sets a pointer for a given varname.'''
        (resource, _) = self._resources[varname]
        self._resources[varname] = (resource, pointer)
    

    def has(self, varname):
        '''Returns a boolean, iff varname is already set.'''
        return varname in self._resources
    
    
    def get(self, varname):
        '''Returns resource, pointer for the resource with the given varname.'''
        return self._resources[varname]
    
    
    def getAll(self):
        '''Returns a dict of resources, key:varname, value:(routine, pointer)'''
        return self._resources
    
    
    def getAST(self, varname):
        '''Returns an AST node for the given varname.'''
        (resource, pointer) = self._resources[varname]
        
        if isinstance(resource, Routine):
            return ASTRoutine(varname, resource.ast())
        
        elif isinstance(resource, PokeString):
            return ASTResourceString(varname, resource)
        
        elif isinstance(resource, PokeMovement):
            return ASTResourceMovement(varname, resource)
        
        else:
            raise Exception("No AST node for %s."%repr(resource))
    
    
    def getASTNodes(self):
        '''Returns a list of all AST Nodes attached to this scriptgroup.'''
        result = []
        for varname, (resource, pointer) in self._resources.items():
            result.append(self.getAST(varname))
            
        return result
    
    
    def getPointerlist(self):
        '''Returns a dict of key:varname value:pointer.'''
        pointerlist = {}
        for varname, (resource, pointer) in self._resources.items():
            pointerlist[varname] = pointer
        return pointerlist


    def getPointerVarnamelist(self):
        '''Returns a dict of key:pointer, value:varname.'''
        pointerlist = {}
        for varname, (resource, pointer) in self._resources.items():
            if pointer != None:
                pointerlist[pointer] = varname
        return pointerlist


    def pointers2varnames(self):
        '''Tries to update pointers to their corresponding varnames where possible.'''
        pointerlist = self.getPointerVarnamelist()
        
        #This will not work if the root node is an ASTPointerRef
        rewriter = PointerToVarnameRewriter(pointerlist)
        for astnode in self.getASTNodes():
            astnode.rewriteASTs(rewriter)
            
            
class PointerToVarnameRewriter(ASTRewriter):
    def __init__(self, pointervarnamelists):
        self.l = pointervarnamelists
    
    def rewrite(self, astnode):
        if isinstance(astnode, ASTPointerRef):
            pointer = astnode.getPointer()
            if pointer in self.l:
                return ASTRef(self.l[pointer])
        
        #The node itself is not rewritten, but possibly childnoes have to be
        # rewritten
        else:
            astnode.rewriteASTs(self)

        raise NoRewriteChange()
    