import React, { createContext, useContext, useReducer } from "react";

const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};

// 초기 상태
const initialState = {
  loading: false,
  error: null,
  projects: [],
  currentProject: null,
  promptCards: [],
  categories: [],
  mode: null, // 'user' 또는 'admin'
};

// 액션 타입
const actionTypes = {
  SET_LOADING: "SET_LOADING",
  SET_ERROR: "SET_ERROR",
  SET_PROJECTS: "SET_PROJECTS",
  SET_CURRENT_PROJECT: "SET_CURRENT_PROJECT",
  SET_PROMPT_CARDS: "SET_PROMPT_CARDS",
  SET_CATEGORIES: "SET_CATEGORIES",
  SET_MODE: "SET_MODE",
  ADD_PROJECT: "ADD_PROJECT",
  UPDATE_PROJECT: "UPDATE_PROJECT",
  DELETE_PROJECT: "DELETE_PROJECT",
  ADD_PROMPT_CARD: "ADD_PROMPT_CARD",
  UPDATE_PROMPT_CARD: "UPDATE_PROMPT_CARD",
  DELETE_PROMPT_CARD: "DELETE_PROMPT_CARD",
};

// 리듀서
const appReducer = (state, action) => {
  switch (action.type) {
    case actionTypes.SET_LOADING:
      return { ...state, loading: action.payload };

    case actionTypes.SET_ERROR:
      return { ...state, error: action.payload };

    case actionTypes.SET_PROJECTS:
      return { ...state, projects: action.payload };

    case actionTypes.SET_CURRENT_PROJECT:
      return { ...state, currentProject: action.payload };

    case actionTypes.SET_PROMPT_CARDS:
      return { ...state, promptCards: action.payload };

    case actionTypes.SET_CATEGORIES:
      return { ...state, categories: action.payload };

    case actionTypes.SET_MODE:
      return { ...state, mode: action.payload };

    case actionTypes.ADD_PROJECT:
      return {
        ...state,
        projects: [...state.projects, action.payload],
      };

    case actionTypes.UPDATE_PROJECT:
      return {
        ...state,
        projects: state.projects.map((project) =>
          project.projectId === action.payload.projectId
            ? { ...project, ...action.payload }
            : project
        ),
        currentProject:
          state.currentProject?.projectId === action.payload.projectId
            ? { ...state.currentProject, ...action.payload }
            : state.currentProject,
      };

    case actionTypes.DELETE_PROJECT:
      return {
        ...state,
        projects: state.projects.filter(
          (project) => project.projectId !== action.payload
        ),
        currentProject:
          state.currentProject?.projectId === action.payload
            ? null
            : state.currentProject,
      };

    case actionTypes.ADD_PROMPT_CARD:
      return {
        ...state,
        promptCards: [...state.promptCards, action.payload],
      };

    case actionTypes.UPDATE_PROMPT_CARD:
      return {
        ...state,
        promptCards: state.promptCards.map((card) =>
          card.promptId === action.payload.promptId
            ? { ...card, ...action.payload }
            : card
        ),
      };

    case actionTypes.DELETE_PROMPT_CARD:
      return {
        ...state,
        promptCards: state.promptCards.filter(
          (card) => card.promptId !== action.payload
        ),
      };

    default:
      return state;
  }
};

export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // 액션 크리에이터들
  const actions = {
    setLoading: (loading) =>
      dispatch({ type: actionTypes.SET_LOADING, payload: loading }),
    setError: (error) =>
      dispatch({ type: actionTypes.SET_ERROR, payload: error }),
    setProjects: (projects) =>
      dispatch({ type: actionTypes.SET_PROJECTS, payload: projects }),
    setCurrentProject: (project) =>
      dispatch({ type: actionTypes.SET_CURRENT_PROJECT, payload: project }),
    setPromptCards: (cards) =>
      dispatch({ type: actionTypes.SET_PROMPT_CARDS, payload: cards }),
    setCategories: (categories) =>
      dispatch({ type: actionTypes.SET_CATEGORIES, payload: categories }),
    setMode: (mode) => dispatch({ type: actionTypes.SET_MODE, payload: mode }),
    addProject: (project) =>
      dispatch({ type: actionTypes.ADD_PROJECT, payload: project }),
    updateProject: (project) =>
      dispatch({ type: actionTypes.UPDATE_PROJECT, payload: project }),
    deleteProject: (projectId) =>
      dispatch({ type: actionTypes.DELETE_PROJECT, payload: projectId }),
    addPromptCard: (card) =>
      dispatch({ type: actionTypes.ADD_PROMPT_CARD, payload: card }),
    updatePromptCard: (card) =>
      dispatch({ type: actionTypes.UPDATE_PROMPT_CARD, payload: card }),
    deletePromptCard: (cardId) =>
      dispatch({ type: actionTypes.DELETE_PROMPT_CARD, payload: cardId }),
  };

  const value = {
    ...state,
    ...actions,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export default AppContext;
